#ifndef	_PIC_H_
#define	_PIC_H_

#ifndef _HTC_H_
#include <htc.h>
#endif

#ifdef _HAS_OSCVAL_
extern unsigned char __osccal_val(void);
#endif

#include <chip_select.h>

/* MPLAB REAL-ICE related macros & includes (currently enhanced PICs only) */
#if defined(__DISABLE_REALICE_IT) || !defined(__MPLAB_REALICE__) || !defined(_PIC14E)
	#define __TRACE(id)         /* TRACE disabled */
	#define __LOG(id,value)     /* LOG disabled */
#else
	#if defined(__MPLAB_REALICE__)
		#include <trace16.h>
	#endif
#endif

#define	CLRWDT()	asm("clrwdt")
#define	SLEEP()		asm("sleep")
// function version of nop
#pragma inline(_nop)
extern void _nop(void);
#define NOP()		_nop()

#ifdef _PIC14E
#define RESET()		asm("reset");
#endif

#define	ASMOPT_ON()		asm("opt asmopt_on")
#define	ASMOPT_OFF()	asm("opt asmopt_off")

#define	__CONFIG(x)	asm("\tpsect config,class=CONFIG,delta=2");\
			asm("\tdw "___mkstr(x))

// Programs the lower 4 bits per ID location
#define __IDLOC(w)       asm("\tpsect idloc,class=IDLOC,delta=2");\
			 asm("\tglobal\tidloc_word"); \
			 asm("idloc_word"); \
			 asm("\tirpc\t__arg," ___mkstr(w)); \
			 asm("\tdw 0&__arg&h"); \
			 asm("\tendm")

// Variant of IDLOC for those devices that permit programming of the lower 7 bits per ID location
#define __IDLOC7(a,b,c,d) asm("\tpsect idloc,class=IDLOC,delta=2");\
			 asm("\tglobal\tidloc_word"); \
			 asm("idloc_word"); \
			 asm("\tdw 0x7f&"___mkstr(a)); \
			 asm("\tdw 0x7f&"___mkstr(b)); \
			 asm("\tdw 0x7f&"___mkstr(c)); \
			 asm("\tdw 0x7f&"___mkstr(d))

#if !defined(_PIC14E) && !defined(EEADRL)
#define EEADRL EEADR
#endif
#if	EEPROM_SIZE > 0
#define __EEPROM_DATA(a, b, c, d, e, f, g, h) \
			 asm("\tpsect eeprom_data,class=EEDATA,delta=2,space=2"); \
			 asm("\tdb\t" ___mkstr(a) "," ___mkstr(b) "," ___mkstr(c) "," ___mkstr(d) "," \
				      ___mkstr(e) "," ___mkstr(f) "," ___mkstr(g) "," ___mkstr(h))
#endif

/***********************************************************************
 **** FLASH memory read/write/erase macros and function definitions ****
 ***********************************************************************
 * Notes:
 *	__FLASHTYPE == 0 defined in devices that can only read flash memory - cannot write eg. 16F777
 *	__FLASHTYPE == 1 defined in traditional devices that can write 1 word at a time eg. 16F877
 *	__FLASHTYPE == 2 defined in devices that can only write in 4 word blocks eg. 16F877A
 *	__FLASHTYPE == 3 defined in devices requiring 32-word block erasure before writing eg. 16F87
 *	__FLASHTYPE == undefined if device can neither read nor write program memory
 */
// macro FLASH_READ returns a word stored at a flash address
#if defined(__FLASHTYPE)
extern unsigned int flash_read(unsigned short addr);
#if	EEPROM_SIZE > 0
#define FLASH_READ(addr) \
	(EEADRL=(addr)&0xff,	\
	EEADRH=(addr)>>8,	\
	WREN=0,			\
	EECON1 |= 0x80,		\
	RD=1,			\
	NOP(),			\
	NOP(),			\
	(EEDATH << 8) | EEDATA)
#else	// FLASH_READ without EEPROM
#define FLASH_READ(addr) \
	(EEADRL=(addr)&0xff,	\
	EEADRH=(addr)>>8,	\
	RD=1,			\
	NOP(),			\
	NOP(),			\
	(EEDATH << 8) | EEDATA)
#endif
#endif	// end FLASH_READ

// macro FLASH_WRITE used when writing only one word of data
#if	__FLASHTYPE==2 || __FLASHTYPE==3
/*
 * This is not available in this version. Contact HI-TECH support for more information.
#define FLASH_WRITE(addr,data)	\
	do{	\
	unsigned short x=data;	\
	flash_copy((const unsigned short *)&x,1,addr);	\
	}while(0)

extern void flash_copy(const unsigned short * source_addr,unsigned char length,unsigned short dest_addr);
*/
#elif	__FLASHTYPE==1
#define FLASH_WRITE(addr, value) \
	EEADRL=((addr)&0xff);	\
	EEADRH=((addr)>>8);	\
	EEDATH=((value)>>8);	\
	EEDATA=((value)&0xff);	\
	EECON1 |= 0x80;		\
	WREN=1;			\
	EECON2 = 0x55;		\
	EECON2 = 0xaa;		\
	WR=1;			\
	NOP();		\
	NOP();		\
	WREN=0
//extern void flash_copy(const unsigned short * source_addr,unsigned char length,unsigned short dest_addr);
#endif	// end FLASH_WRITE

// macro FLASH_ERASE used to clear a 32-Byte sector of flash
#if	__FLASHTYPE==3
#define FLASH_ERASE(addr) \
       	while(WR)continue; \
	EEADRL=((addr)&0xFF); \
	EEADRH=((addr>>8)&0xFF); \
	EECON1=0x94; \
	CARRY=0;if(GIE)CARRY=1;GIE=0;\
	EECON2=0x55;EECON2=0xAA;WR=1; \
	NOP(); \
	if(CARRY)GIE=1 

	// library function version
extern void flash_erase(unsigned short addr);
#endif	// end FLASH_ERASE

#include <eeprom_routines.h>

#ifdef __PICCPRO__
/****************************************************************/
/* Built-in delay routine					*/
/****************************************************************/
#pragma inline(_delay)
extern void _delay(unsigned long);
// NOTE: To use the macros below, YOU must have previously defined _XTAL_FREQ
#define __delay_us(x) _delay((unsigned long)((x)*(_XTAL_FREQ/4000000.0)))
#define __delay_ms(x) _delay((unsigned long)((x)*(_XTAL_FREQ/4000.0)))
#endif

/****************************************************************/
/****** Global interrupt enable/disable macro definitions *******/
/****************************************************************/
#if defined(_PIC14) || defined(_PIC14E)
	
#ifndef	ei
#define	ei()	(GIE = 1)	// interrupt enable bit
#endif  

#if defined(_14000) ||  defined(_16C61) || defined(_16C62) ||\
	defined(_16C63) || defined(_16C63A) || defined(_16C64) ||\
	defined(_16C65) || defined(_16C65B) || defined(_16C71) ||\
	defined(_16C73) || defined(_16C73B) || defined(_16C74) ||\
	defined(_16C74B) || defined(_16C84) || defined(_16C745) ||\
	defined(_16C765) || defined(_16LC74B)
	#ifndef	di
		#define di()	{ do { GIE = 0; } while ( GIE == 1 ); }	// disable interrupt bit
	#endif  
#else
	#ifndef	di
		#define	di()	(GIE = 0)	// interrupt enable bit
	#endif  
#endif

#endif

#ifdef __RESETBITS_ADDR
/* If '--runtime=+resetbits' is specified, these reflect the state
   of TO and PD, respectively, which are trashed by startup code. */
unsigned char __resetbits @ __RESETBITS_ADDR;
bit __powerdown	@ ((unsigned)&__resetbits*8)+3;
bit __timeout	@ ((unsigned)&__resetbits*8)+4;
#endif
#endif	/* _PIC_H */
