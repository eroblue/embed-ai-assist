/*
 * STM32F103ZET6 (high-density, 512KB Flash / 64KB SRAM) GNU ld 链接脚本
 *
 * 平台资料库提供：S7b 阶段 A' 在工程内无用户自维护 .ld 时直接引用本脚本。
 * 符号约定与平台库 GNU 启动文件（sdk/startup/gcc_ride7/startup_stm32f10x_hd.s）
 * 对齐：_estack / _sidata / _sdata / _edata / _sbss / _ebss、.isr_vector 段。
 * 内存布局依据：STM32F103ZET6 数据手册（FLASH 0x08000000 512K，SRAM 0x20000000 64K）。
 */
ENTRY(Reset_Handler)

_Min_Heap_Size  = 0x200;   /* 512B 堆（malloc 用；纯裸机可改 0） */
_Min_Stack_Size = 0x400;   /* 1KB 栈 */

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);    /* 栈顶 = RAM 末尾（Cortex-M 满递减栈） */

SECTIONS
{
  .isr_vector :
  {
    . = ALIGN(4);
    KEEP(*(.isr_vector))
    . = ALIGN(4);
  } > FLASH

  .text :
  {
    . = ALIGN(4);
    *(.text*)
    *(.rodata*)
    KEEP(*(.init))
    KEEP(*(.fini))
    . = ALIGN(4);
    _etext = .;
  } > FLASH

  .ARM.extab   : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > FLASH
  .ARM.exidx   : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH

  /* .data 初值在 FLASH，启动时由 Reset_Handler 拷贝到 RAM */
  _sidata = LOADADDR(.data);
  .data :
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data*)
    . = ALIGN(4);
    _edata = .;
  } > RAM AT > FLASH

  .bss (NOLOAD) :
  {
    . = ALIGN(4);
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM

  ._user_heap_stack (NOLOAD) :
  {
    . = ALIGN(8);
    PROVIDE(end = .);
    . = . + _Min_Heap_Size + _Min_Stack_Size;
    . = ALIGN(8);
  } > RAM

  /DISCARD/ : { *(.comment) }
}