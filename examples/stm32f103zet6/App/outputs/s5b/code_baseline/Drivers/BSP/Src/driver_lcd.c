/**
 * @file    driver_lcd.c
 * @brief   TFT_LCD 显示驱动实现（NT35510，480x800，16 位并口 8080）
 *
 * 面板为 4.3 寸 480x800 TFTLCD 模块（Alientek 战舰V3 配套），控制器 NT35510。
 * 与 ILI9341 类面板的关键差异（本文件按 NT35510 实现）：
 *  - 指令为 16 位，命令字落在总线高字节；CASET/RASET 是"一条指令带一个 8 位参数"
 *    （0x2A00~0x2A03 / 0x2B00~0x2B03），RAMWR=0x2C00、MADCTL=0x3600、COLMOD=0x3A00、
 *    SLPOUT=0x1100、DISPON=0x2900、SWRESET=0x0100（NT35510 数据手册指令集）；
 *  - 分辨率 480x800（竖屏），16 位色 RGB565；
 *  - 上电需先按页解锁（0xF000=0x55 / 0xF001=0xAA / 0xF002=0x52）再写电源与伽马参数。
 *
 * 上电寄存器序列取自 NT35510 应用手册"软件设定流程"的公开参考实现（NT35510 数据手册
 * 指令集 + 正点原子/洋桃电子 4.3 寸 NT35510 模块驱动），不自行臆造寄存器。
 * 硬件访问全部经 par_port，延时经 timer_port，无任何厂商 HAL 依赖。
 * 竖屏方向（MADCTL 0x00 = 从左到右/从上到下）；若面板装配方向不同，改 LCD_MADCTL_PORTRAIT。
 */
#include "driver_lcd.h"
#include "par_port.h"
#include "timer_port.h"
#include <string.h>

/* 联调诊断日志：置 1 时经 uart_port 输出 LCD 初始化步骤/ID/寄存器回读
   （与 5s JSON 上报共用 USART1，仅联调用，定位完成后置 0）。 */
#define DRIVER_LCD_DIAG_LOG  1u

#if DRIVER_LCD_DIAG_LOG
#include "uart_port.h"
static void lcd_diag_str(const char *s);
static void lcd_diag_hex(uint16_t v);
#else
#define lcd_diag_str(s)      ((void)0)
#define lcd_diag_hex(v)      ((void)0)
#endif

#define LCD_WIDTH         480u   /* 竖屏宽（短边） */
#define LCD_HEIGHT        800u   /* 竖屏高（长边） */
#define LCD_CHAR_W         16u   /* 8x16 字模 x2（水平） */
#define LCD_CHAR_H         32u   /* 8x16 字模 x2（垂直） */

/* ---- NT35510 指令（16 位，命令字含参数索引） ---- */
#define LCD_CMD_SWRESET    0x0100u   /* 软复位 */
#define LCD_CMD_SLPOUT     0x1100u   /* 退出睡眠 */
#define LCD_CMD_DISPON     0x2900u   /* 开显示 */
#define LCD_CMD_DISPOFF    0x2800u   /* 关显示 */
#define LCD_CMD_CASET      0x2A00u   /* 列地址 0x2A00~0x2A03：每条带 1 个 8 位参数 */
#define LCD_CMD_RASET      0x2B00u   /* 行地址 0x2B00~0x2B03：每条带 1 个 8 位参数 */
#define LCD_CMD_RAMWR      0x2C00u   /* 写显存（连续写，地址自增） */
#define LCD_CMD_MADCTL     0x3600u   /* 扫描方向（MY/MX/MV） */
#define LCD_CMD_COLMOD     0x3A00u   /* 像素格式（0x55 = 16 位 RGB565） */
#define LCD_CMD_RDDCOLMOD  0x0C00u   /* 回读像素格式（期望 0x55） */
#define LCD_CMD_RDID_PID   0xDA00u   /* 读产品 ID（8 位参数） */
#define LCD_CMD_RDID_VER   0xDB00u   /* 读控制器版本 ID */
#define LCD_CMD_RDID_CID   0xDC00u   /* 读控制器 ID */

/* 竖屏扫描方向：从左到右、从上到下（MY=0/MX=0/MV=0，正点原子默认扫描方向） */
#define LCD_MADCTL_PORTRAIT  0x00u

/* 颜色（RGB565） */
#define LCD_COLOR_FG       0xFFFFu   /* 前景：白 */
#define LCD_COLOR_BG       0x0000u   /* 背景：黑 */

/* ---------------- 8x16 ASCII 字形（页分块：[0..7]=上页列0-7，[8..15]=下页列0-7，bit7=最上行） ---------------- */
static const uint8_t s_lcd_font[][16] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}, /* ' ' */
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x80,0x80,0x80,0x80,0x80,0x80}, /* '-' */
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x00,0x00,0x00,0x00,0x00}, /* '.' */
    {0x00,0x07,0x08,0x10,0x10,0x08,0x07,0x00,0x00,0xF0,0x08,0x04,0x04,0x08,0xF0,0x00}, /* '0' */
    {0x00,0x08,0x08,0x1F,0x00,0x00,0x00,0x00,0x00,0x04,0x04,0xFC,0x04,0x04,0x00,0x00}, /* '1' */
    {0x00,0x0E,0x10,0x10,0x10,0x11,0x0E,0x00,0x00,0x0C,0x14,0x24,0x44,0x84,0x0C,0x00}, /* '2' */
    {0x00,0x0C,0x10,0x11,0x11,0x12,0x0C,0x00,0x00,0x18,0x04,0x04,0x04,0x88,0x70,0x00}, /* '3' */
    {0x00,0x00,0x03,0x04,0x08,0x1F,0x00,0x00,0x00,0xE0,0x20,0x24,0x24,0xFC,0x24,0x00}, /* '4' */
    {0x00,0x1F,0x10,0x11,0x11,0x10,0x10,0x00,0x00,0x98,0x84,0x04,0x04,0x88,0x70,0x00}, /* '5' */
    {0x00,0x07,0x08,0x11,0x11,0x18,0x00,0x00,0x00,0xF0,0x88,0x04,0x04,0x88,0x70,0x00}, /* '6' */
    {0x00,0x1C,0x10,0x10,0x13,0x1C,0x10,0x00,0x00,0x00,0x00,0xFC,0x00,0x00,0x00,0x00}, /* '7' */
    {0x00,0x0E,0x11,0x10,0x10,0x11,0x0E,0x00,0x00,0x38,0x44,0x84,0x84,0x44,0x38,0x00}, /* '8' */
    {0x00,0x07,0x08,0x10,0x10,0x08,0x07,0x00,0x00,0x00,0x8C,0x44,0x44,0x88,0xF0,0x00}, /* '9' */
    {0x00,0x00,0x00,0x03,0x03,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x00,0x00,0x00}, /* ':' */
    {0x00,0x00,0x00,0x00,0x01,0x06,0x18,0x20,0x00,0x06,0x18,0x60,0x80,0x00,0x00,0x00}, /* '/' */
    {0x0F,0x10,0x0F,0x00,0x07,0x18,0x00,0x00,0x00,0x84,0x38,0xC0,0x78,0x84,0x78,0x00}, /* '%' */
    {0x00,0x00,0x03,0x1C,0x07,0x00,0x00,0x00,0x04,0x3C,0xC4,0x40,0x40,0xE4,0x1C,0x04}, /* 'A' */
    {0x10,0x1F,0x11,0x11,0x11,0x0E,0x00,0x00,0x04,0xFC,0x04,0x04,0x04,0x88,0x70,0x00}, /* 'B' */
    {0x03,0x0C,0x10,0x10,0x10,0x10,0x1C,0x00,0xE0,0x18,0x04,0x04,0x04,0x08,0x10,0x00}, /* 'C' */
    {0x10,0x1F,0x10,0x10,0x10,0x08,0x07,0x00,0x04,0xFC,0x04,0x04,0x04,0x08,0xF0,0x00}, /* 'D' */
    {0x10,0x1F,0x11,0x11,0x17,0x10,0x08,0x00,0x04,0xFC,0x04,0x04,0xC4,0x04,0x18,0x00}, /* 'E' */
    {0x10,0x1F,0x11,0x11,0x17,0x10,0x08,0x00,0x04,0xFC,0x04,0x00,0xC0,0x00,0x00,0x00}, /* 'F' */
    {0x03,0x0C,0x10,0x10,0x10,0x1C,0x00,0x00,0xE0,0x18,0x04,0x04,0x44,0x78,0x40,0x00}, /* 'G' */
    {0x10,0x1F,0x10,0x00,0x00,0x10,0x1F,0x10,0x04,0xFC,0x84,0x80,0x80,0x84,0xFC,0x04}, /* 'H' */
    {0x00,0x10,0x10,0x1F,0x10,0x10,0x00,0x00,0x00,0x04,0x04,0xFC,0x04,0x04,0x00,0x00}, /* 'I' */
    {0x00,0x00,0x10,0x10,0x1F,0x10,0x10,0x00,0x03,0x01,0x01,0x01,0xFE,0x00,0x00,0x00}, /* 'J' */
    {0x10,0x1F,0x11,0x03,0x14,0x18,0x10,0x00,0x04,0xFC,0x04,0x80,0x64,0x1C,0x04,0x00}, /* 'K' */
    {0x10,0x1F,0x10,0x00,0x00,0x00,0x00,0x00,0x04,0xFC,0x04,0x04,0x04,0x04,0x0C,0x00}, /* 'L' */
    {0x10,0x1F,0x1F,0x00,0x1F,0x1F,0x10,0x00,0x04,0xFC,0x00,0xFC,0x00,0xFC,0x04,0x00}, /* 'M' */
    {0x10,0x1F,0x0C,0x03,0x00,0x10,0x1F,0x10,0x04,0xFC,0x04,0x00,0xE0,0x18,0xFC,0x00}, /* 'N' */
    {0x07,0x08,0x10,0x10,0x10,0x08,0x07,0x00,0xF0,0x08,0x04,0x04,0x04,0x08,0xF0,0x00}, /* 'O' */
    {0x10,0x1F,0x10,0x10,0x10,0x10,0x0F,0x00,0x04,0xFC,0x84,0x80,0x80,0x80,0x00,0x00}, /* 'P' */
    {0x07,0x08,0x10,0x10,0x10,0x08,0x07,0x00,0xF0,0x18,0x24,0x24,0x1C,0x0A,0xF2,0x00}, /* 'Q' */
    {0x10,0x1F,0x11,0x11,0x11,0x11,0x0E,0x00,0x04,0xFC,0x04,0x00,0xC0,0x30,0x0C,0x04}, /* 'R' */
    {0x00,0x0E,0x11,0x10,0x10,0x10,0x1C,0x00,0x00,0x1C,0x04,0x84,0x84,0x44,0x38,0x00}, /* 'S' */
    {0x18,0x10,0x10,0x1F,0x10,0x10,0x18,0x00,0x00,0x00,0x04,0xFC,0x04,0x00,0x00,0x00}, /* 'T' */
    {0x10,0x1F,0x10,0x00,0x00,0x10,0x1F,0x10,0x00,0xF8,0x04,0x04,0x04,0x04,0xF8,0x00}, /* 'U' */
    {0x10,0x1E,0x11,0x00,0x00,0x13,0x1C,0x10,0x00,0x00,0xE0,0x1C,0x70,0x80,0x00,0x00}, /* 'V' */
    {0x1F,0x10,0x00,0x1F,0x00,0x10,0x1F,0x00,0xC0,0x3C,0xE0,0x00,0xE0,0x3C,0xC0,0x00}, /* 'W' */
    {0x10,0x18,0x16,0x01,0x01,0x16,0x18,0x10,0x04,0x0C,0x34,0xC0,0xC0,0x34,0x0C,0x04}, /* 'X' */
    {0x10,0x1C,0x13,0x00,0x13,0x1C,0x10,0x00,0x00,0x00,0x04,0xFC,0x04,0x00,0x00,0x00}, /* 'Y' */
    {0x08,0x10,0x10,0x10,0x13,0x1C,0x10,0x00,0x04,0x1C,0x64,0x84,0x04,0x04,0x18,0x00}, /* 'Z' */
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01}, /* '_' */
};
static const char s_lcd_font_chars[] = " -.0123456789:/%ABCDEFGHIJKLMNOPQRSTUVWXYZ_";

/* ---------------- NT35510 上电寄存器序列 ----------------
 * 组织方式：页 1（电源/伽马参数）→ 伽马表 → 页 0（显示控制/时序/像素格式）→ SLPOUT → DISPON。
 * 页解锁：0xF000=0x55 / 0xF001=0xAA / 0xF002=0x52 / 0xF003=0x08 / 0xF004=页号。
 * 来源：NT35510 应用手册"软件设定流程"公开参考实现（正点原子/洋桃电子 4.3 寸模块驱动），
 * 未经证实不得修改这些寄存器值——电源轨（AVDD/AVEE/VCL/VGH/VGL/VCOM）设错会损伤面板。
 */
typedef struct {
    uint16_t reg;   /* 16 位命令 */
    uint16_t val;   /* 16 位数据（8 位参数，低字节有效） */
} lcd_reg_t;

#define LCD_GAMMA_LEN      52u

/* 伽马参数（0xD1~0xD6 共 6 组，每组 52 个 8 位参数） */
static const uint8_t s_lcd_gamma[LCD_GAMMA_LEN] = {
    0x00,0x33,0x00,0x34,0x00,0x3A,0x00,0x4A,0x00,0x5C,0x00,0x81,0x00,0xA6,0x00,0xE5,
    0x01,0x13,0x01,0x54,0x01,0x82,0x01,0xCA,0x02,0x00,0x02,0x01,0x02,0x34,0x02,0x67,
    0x02,0x84,0x02,0xA4,0x02,0xB7,0x02,0xCF,0x02,0xDE,0x02,0xF2,0x02,0xFE,0x03,0x10,
    0x03,0x33,0x03,0x6D,
};

/* 页 1（LV2 Page 1）：电源轨与伽马参数 */
static const lcd_reg_t s_lcd_init_p1[] = {
    {0xF000u, 0x55u}, {0xF001u, 0xAAu}, {0xF002u, 0x52u}, {0xF003u, 0x08u}, {0xF004u, 0x01u},
    /* AVDD 5.2V */
    {0xB000u, 0x0Du}, {0xB001u, 0x0Du}, {0xB002u, 0x0Du},
    /* AVDD ratio */
    {0xB600u, 0x34u}, {0xB601u, 0x34u}, {0xB602u, 0x34u},
    /* AVEE -5.2V */
    {0xB100u, 0x0Du}, {0xB101u, 0x0Du}, {0xB102u, 0x0Du},
    /* AVEE ratio */
    {0xB700u, 0x34u}, {0xB701u, 0x34u}, {0xB702u, 0x34u},
    /* VCL -2.5V */
    {0xB200u, 0x00u}, {0xB201u, 0x00u}, {0xB202u, 0x00u},
    /* VCL ratio */
    {0xB800u, 0x24u}, {0xB801u, 0x24u}, {0xB802u, 0x24u},
    /* VGH 15V（free pump） */
    {0xBF00u, 0x01u}, {0xB300u, 0x0Fu}, {0xB301u, 0x0Fu}, {0xB302u, 0x0Fu},
    /* VGH ratio */
    {0xB900u, 0x34u}, {0xB901u, 0x34u}, {0xB902u, 0x34u},
    /* VGL -10V */
    {0xB500u, 0x08u}, {0xB501u, 0x08u}, {0xB502u, 0x08u}, {0xC200u, 0x03u},
    /* VGLX ratio */
    {0xBA00u, 0x24u}, {0xBA01u, 0x24u}, {0xBA02u, 0x24u},
    /* VGMP 4.5V / VGSP 0V */
    {0xBC00u, 0x00u}, {0xBC01u, 0x78u}, {0xBC02u, 0x00u},
    /* VGMN -4.5V / VGSN 0V */
    {0xBD00u, 0x00u}, {0xBD01u, 0x78u}, {0xBD02u, 0x00u},
    /* VCOM */
    {0xBE00u, 0x00u}, {0xBE01u, 0x64u},
};

/* 页 0（LV2 Page 0）：显示控制、时序与像素格式 */
static const lcd_reg_t s_lcd_init_p0[] = {
    {0xF000u, 0x55u}, {0xF001u, 0xAAu}, {0xF002u, 0x52u}, {0xF003u, 0x08u}, {0xF004u, 0x00u},
    /* Display control */
    {0xB100u, 0xCCu}, {0xB101u, 0x00u},
    /* Source hold time */
    {0xB600u, 0x05u},
    /* Gate EQ control */
    {0xB700u, 0x70u}, {0xB701u, 0x70u},
    /* Source EQ control（mode 2） */
    {0xB800u, 0x01u}, {0xB801u, 0x03u}, {0xB802u, 0x03u}, {0xB803u, 0x03u},
    /* Inversion mode（2-dot） */
    {0xBC00u, 0x02u}, {0xBC01u, 0x00u}, {0xBC02u, 0x00u},
    /* Timing control 4H w/ 4-delay */
    {0xC900u, 0xD0u}, {0xC901u, 0x02u}, {0xC902u, 0x50u}, {0xC903u, 0x50u}, {0xC904u, 0x50u},
    {0x3500u, 0x00u},
    /* 像素格式：16 位 RGB565 */
    {0x3A00u, 0x55u},
};

/* 字符单元像素缓冲（16x32 = 512 像素；clear 时复用为整行缓冲，480 <= 512） */
static uint16_t s_cell_buf[LCD_CHAR_W * LCD_CHAR_H];

/* ---- 初始化自检记录（联调定位用；判定码见 driver_lcd_get_diag_code） ---- */
static uint8_t  s_diag_id_b0;      /* 0xDA00 回读（产品 ID） */
static uint8_t  s_diag_id_b1;      /* 0xDB00 回读（版本 ID） */
static uint8_t  s_diag_id_b2;      /* 0xDC00 回读（控制器 ID） */
static uint8_t  s_diag_colmod;     /* 0x0C00 回读（期望 0x55） */
static uint8_t  s_diag_no_resp;    /* ID 三字节全相等且为 00/FF = 总线无响应 */
static uint8_t  s_diag_id_ok;      /* ID 属已知 NT35510 特征值 */

static uint8_t lcd_font_index(char ch);
static uint8_t lcd_glyph_bit(const uint8_t *glyph, uint8_t row, uint8_t col);
static int32_t lcd_write_reg(uint16_t reg, uint16_t val);
static int32_t lcd_write_table(const lcd_reg_t *tbl, uint16_t n);
static int32_t lcd_write_gamma_page(void);
static int32_t lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
static int32_t lcd_read_reg8(uint16_t cmd, uint8_t *out);

int32_t driver_lcd_init(void)
{
    int32_t r;
    uint16_t lcd_id = 0u;
    uint8_t colmod = 0u;

    lcd_diag_str("\r\n[LCD] NT35510 init start\r\n");

    r = par_port_init(PAR_PORT_LCD);
    if (r != PORT_OK) { return r; }

    /* 上电稳定：数据手册要求上电后 ≥120ms 才能发命令。面板电源独立于 MCU，
       MCU 复位（如烧录后）时面板未必复位，故再补一次软复位使状态可预测。 */
    (void)timer_port_delay_us(120000u);
    (void)par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_SWRESET);
    (void)timer_port_delay_us(120000u);

    /* 型号探测（诊断关键点）：读不到/读到全 00 或全 FF = 总线无响应 */
    (void)driver_lcd_read_id(&lcd_id);

    /* 厂商寄存器序列：页 1（电源/伽马）→ 伽马表 → 页 0（显示控制/时序/像素格式） */
    r = lcd_write_table(s_lcd_init_p1,
                        (uint16_t)(sizeof(s_lcd_init_p1) / sizeof(s_lcd_init_p1[0])));
    if (r != PORT_OK) { return r; }
    r = lcd_write_gamma_page();
    if (r != PORT_OK) { return r; }
    r = lcd_write_table(s_lcd_init_p0,
                        (uint16_t)(sizeof(s_lcd_init_p0) / sizeof(s_lcd_init_p0[0])));
    if (r != PORT_OK) { return r; }
    lcd_diag_str("[LCD] init seq written\r\n");

    /* 退出睡眠（数据手册典型 120ms） */
    r = par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_SLPOUT);
    if (r != PORT_OK) { return r; }
    (void)timer_port_delay_us(120000u);

    /* 关显示后再设方向/清屏，避免上电瞬间出现乱码 */
    r = par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_DISPOFF);
    if (r != PORT_OK) { return r; }
    r = lcd_write_reg(LCD_CMD_MADCTL, LCD_MADCTL_PORTRAIT);
    if (r != PORT_OK) { return r; }

    /* 回读校验（诊断）：寄存器写没写进去——区分"总线写不进去"与"面板型号不符" */
    if (lcd_read_reg8(LCD_CMD_RDDCOLMOD, &colmod) == PORT_OK) {
        s_diag_colmod = colmod;
        lcd_diag_str("[LCD] RDDCOLMOD(0x0C00)=");
        lcd_diag_hex((uint16_t)colmod);
        lcd_diag_str(" (expect 55)\r\n");
    }

    /* 自检结论：总线完全无响应 → 初始化判失败（上层按 REQ-010 走慢闪 + 跳过显示） */
    if (s_diag_no_resp) {
        lcd_diag_str("[LCD] FAIL: no response on bus "
                     "(check FSMC timing / CS / data lines / panel power)\r\n");
        return PORT_ERR_STATE;
    }

    r = driver_lcd_clear();
    if (r != PORT_OK) { return r; }

    /* 开显示（数据手册典型 20ms） */
    r = par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_DISPON);
    if (r != PORT_OK) { return r; }
    (void)timer_port_delay_us(20000u);

    lcd_diag_str("[LCD] init done code=");
    lcd_diag_hex((uint16_t)driver_lcd_get_diag_code());
    lcd_diag_str("\r\n");
    return PORT_OK;
}

int32_t driver_lcd_read_id(uint16_t *id)
{
    uint8_t b0 = 0u;
    uint8_t b1 = 0u;
    uint8_t b2 = 0u;
    int32_t r;

    if (id == (uint16_t *)0) {
        return PORT_ERR_PARAM;
    }

    /* NT35510 的 ID 由 3 条读指令给出（各 1 个 8 位参数）：
       0xDA00=产品 ID、0xDB00=版本 ID、0xDC00=控制器 ID。
       不同批次/模块的版本字节不同：常见 0x55 或 0x80（正点原子把 0x8000 归一为 0x5510）。 */
    r = lcd_read_reg8(LCD_CMD_RDID_PID, &b0);
    if (r != PORT_OK) { return r; }
    r = lcd_read_reg8(LCD_CMD_RDID_VER, &b1);
    if (r != PORT_OK) { return r; }
    r = lcd_read_reg8(LCD_CMD_RDID_CID, &b2);
    if (r != PORT_OK) { return r; }

    s_diag_id_b0 = b0;
    s_diag_id_b1 = b1;
    s_diag_id_b2 = b2;
    *id = (uint16_t)(((uint16_t)b1 << 8) | (uint16_t)b2);

    s_diag_no_resp = (uint8_t)(((b0 == b1) && (b1 == b2) &&
                                ((b0 == 0x00u) || (b0 == 0xFFu))) ? 1u : 0u);
    s_diag_id_ok = (uint8_t)(((*id == 0x5510u) || (*id == 0x8000u)) ? 1u : 0u);

    lcd_diag_str("[LCD] ID(DA/DB/DC)=");
    lcd_diag_hex((uint16_t)b0);
    lcd_diag_str(" ");
    lcd_diag_hex((uint16_t)b1);
    lcd_diag_str(" ");
    lcd_diag_hex((uint16_t)b2);
    lcd_diag_str(" -> id=");
    lcd_diag_hex(*id);
    lcd_diag_str(s_diag_no_resp ? " (NO RESPONSE!)\r\n"
                                : (s_diag_id_ok ? " (NT35510)\r\n"
                                                : " (unrecognized ID)\r\n"));
    return PORT_OK;
}

int32_t driver_lcd_clear(void)
{
    int32_t r;
    uint16_t x;
    uint16_t y;

    r = lcd_set_window(0u, 0u, (uint16_t)(LCD_WIDTH - 1u), (uint16_t)(LCD_HEIGHT - 1u));
    if (r != PORT_OK) { return r; }

    /* 复用单元缓冲作整行缓冲（512 >= 480） */
    for (x = 0u; x < LCD_WIDTH; x++) {
        s_cell_buf[x] = LCD_COLOR_BG;
    }
    for (y = 0u; y < LCD_HEIGHT; y++) {
        r = par_port_write_data_block(PAR_PORT_LCD, s_cell_buf, LCD_WIDTH);
        if (r != PORT_OK) { return r; }
    }
    return PORT_OK;
}

int32_t driver_lcd_show_line(uint8_t line, const char *text)
{
    int32_t r;
    uint16_t col;
    uint16_t y0;

    if ((line >= DRIVER_LCD_LINES) || (text == 0)) {
        return PORT_ERR_PARAM;
    }
    y0 = (uint16_t)line * LCD_CHAR_H;

    /* 逐字符渲染整行（文本不足 30 列时以空格补齐；'\0' 之后按空格处理） */
    for (col = 0u; col < DRIVER_LCD_LINE_CHARS; col++) {
        char ch = *text;
        const uint8_t *glyph;
        uint16_t idx = 0u;
        uint8_t cr;

        if (ch != (char)0) {
            text++;
        }
        glyph = s_lcd_font[lcd_font_index(ch)];

        /* 8x16 字模 2 倍放大填充 16x32 单元（每字形行重复两次、每字形列重复两次） */
        for (cr = 0u; cr < LCD_CHAR_H; cr++) {
            uint8_t gr = (uint8_t)(cr >> 1);   /* 字形行 0..15 */
            uint8_t gc;
            for (gc = 0u; gc < 8u; gc++) {
                uint16_t px = lcd_glyph_bit(glyph, gr, gc) ? LCD_COLOR_FG : LCD_COLOR_BG;
                s_cell_buf[idx++] = px;
                s_cell_buf[idx++] = px;        /* 水平 x2 */
            }
        }

        r = lcd_set_window((uint16_t)(col * LCD_CHAR_W), y0,
                           (uint16_t)(col * LCD_CHAR_W + LCD_CHAR_W - 1u),
                           (uint16_t)(y0 + LCD_CHAR_H - 1u));
        if (r != PORT_OK) { return r; }
        r = par_port_write_data_block(PAR_PORT_LCD, s_cell_buf,
                                      (uint32_t)(LCD_CHAR_W * LCD_CHAR_H));
        if (r != PORT_OK) { return r; }
    }
    return PORT_OK;
}

int32_t driver_lcd_deinit(void)
{
    (void)par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_DISPOFF);
    return par_port_deinit(PAR_PORT_LCD);
}

/** 初始化自检结果码（判定优先级：无响应 > ID 不符 > 寄存器回读异常）。 */
uint8_t driver_lcd_get_diag_code(void)
{
    if (s_diag_no_resp) { return 1u; }
    if (!s_diag_id_ok) { return 2u; }
    if (s_diag_colmod != 0x55u) { return 3u; }
    return 0u;
}

/** 自检摘要（经 uart_port；DRIVER_LCD_DIAG_LOG=0 时为空操作）。 */
void driver_lcd_diag_dump(void)
{
    lcd_diag_str("[LCD] diag code=");
    lcd_diag_hex((uint16_t)driver_lcd_get_diag_code());
    lcd_diag_str(" id=");
    lcd_diag_hex((uint16_t)s_diag_id_b0);
    lcd_diag_str(" ");
    lcd_diag_hex((uint16_t)s_diag_id_b1);
    lcd_diag_str(" ");
    lcd_diag_hex((uint16_t)s_diag_id_b2);
    lcd_diag_str(" colmod=");
    lcd_diag_hex((uint16_t)s_diag_colmod);
    lcd_diag_str(" (0=ok 1=no-resp 2=wrong-id 3=reg-read)\r\n");
}

/** 写一个寄存器（16 位命令 + 16 位数据）。 */
static int32_t lcd_write_reg(uint16_t reg, uint16_t val)
{
    int32_t r = par_port_write_cmd(PAR_PORT_LCD, reg);
    if (r != PORT_OK) { return r; }
    return par_port_write_data(PAR_PORT_LCD, val);
}

/** 顺序写一张寄存器表。 */
static int32_t lcd_write_table(const lcd_reg_t *tbl, uint16_t n)
{
    uint16_t i;
    int32_t r;

    for (i = 0u; i < n; i++) {
        r = lcd_write_reg(tbl[i].reg, tbl[i].val);
        if (r != PORT_OK) { return r; }
    }
    return PORT_OK;
}

/** 写伽马表：0xD100~0xD133 … 0xD600~0xD633（6 组 × 52 个 8 位参数）。 */
static int32_t lcd_write_gamma_page(void)
{
    uint16_t page;
    uint16_t i;
    int32_t r;

    for (page = 0xD1u; page <= 0xD6u; page++) {
        for (i = 0u; i < LCD_GAMMA_LEN; i++) {
            r = lcd_write_reg((uint16_t)((page << 8) | i), (uint16_t)s_lcd_gamma[i]);
            if (r != PORT_OK) { return r; }
        }
    }
    return PORT_OK;
}

/** 字符集查找：未收录字符回落为空格。 */
static uint8_t lcd_font_index(char ch)
{
    const char *hit;
    if (ch == (char)0) {
        return 0u; /* 字符串结束后的填充位 = 空格 */
    }
    hit = strchr(s_lcd_font_chars, ch);
    if ((hit == 0) || (*hit == (char)0)) {
        return 0u;
    }
    return (uint8_t)(hit - s_lcd_font_chars);
}

/** 页分块字模取位：[col]=上页列（行0-7），[8+col]=下页列（行8-15），**bit7=最上行**。
 *  字模取自正点原子 oledfont 约定：字节内 MSB 为首行（逐位左移即为自上而下），
 *  按 bit0 取位会把整个字形上下镜像（表现为"位置对但字全乱"）。 */
static uint8_t lcd_glyph_bit(const uint8_t *glyph, uint8_t row, uint8_t col)
{
    if (row < 8u) {
        return (uint8_t)((glyph[col] >> (7u - row)) & 1u);
    }
    return (uint8_t)((glyph[8u + col] >> (7u - (row - 8u))) & 1u);
}

/** 设置写入窗口：CASET（列，0x2A00~0x2A03）+ RASET（行，0x2B00~0x2B03）+ RAMWR。
 *  NT35510 与 ILI9341 不同：每条坐标指令只带 1 个 8 位参数，需分别下发 4 条。 */
static int32_t lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    int32_t r;

    r = lcd_write_reg((uint16_t)(LCD_CMD_CASET + 0u), (uint16_t)(x0 >> 8));
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_CASET + 1u), (uint16_t)(x0 & 0xFFu)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_CASET + 2u), (uint16_t)(x1 >> 8)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_CASET + 3u), (uint16_t)(x1 & 0xFFu)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_RASET + 0u), (uint16_t)(y0 >> 8)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_RASET + 1u), (uint16_t)(y0 & 0xFFu)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_RASET + 2u), (uint16_t)(y1 >> 8)); }
    if (r == PORT_OK) { r = lcd_write_reg((uint16_t)(LCD_CMD_RASET + 3u), (uint16_t)(y1 & 0xFFu)); }
    if (r == PORT_OK) { r = par_port_write_cmd(PAR_PORT_LCD, LCD_CMD_RAMWR); }
    return r;
}

/** 读一个 8 位寄存器（写命令 → 短暂延时 → 读数据）。 */
static int32_t lcd_read_reg8(uint16_t cmd, uint8_t *out)
{
    uint16_t raw = 0u;
    int32_t r;

    r = par_port_write_cmd(PAR_PORT_LCD, cmd);
    if (r != PORT_OK) { return r; }
    (void)timer_port_delay_us(5u);
    r = par_port_read_data(PAR_PORT_LCD, &raw);
    if (r != PORT_OK) { return r; }
    /* 8 位参数在 16 位总线上的落位随模块接线不同（低字节或高字节），
       取两者之或即可还原（其中一个必为 0） */
    *out = (uint8_t)((raw & 0xFFu) | (raw >> 8));
    return PORT_OK;
}

#if DRIVER_LCD_DIAG_LOG
/** 诊断输出：字符串（经 uart_port 同步写）。 */
static void lcd_diag_str(const char *s)
{
    uint16_t n = 0u;
    while (s[n] != '\0') {
        n++;
    }
    (void)uart_port_write(UART_PORT_REPORT, (const uint8_t *)s, n);
}

/** 诊断输出：4 位十六进制。 */
static void lcd_diag_hex(uint16_t v)
{
    static const char hexd[] = "0123456789ABCDEF";
    char out[5];
    out[0] = hexd[(v >> 12) & 0x0Fu];
    out[1] = hexd[(v >> 8) & 0x0Fu];
    out[2] = hexd[(v >> 4) & 0x0Fu];
    out[3] = hexd[v & 0x0Fu];
    out[4] = '\0';
    lcd_diag_str(out);
}
#endif /* DRIVER_LCD_DIAG_LOG */
