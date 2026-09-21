opt subtitle "HI-TECH Software Omniscient Code Generator (PRO mode) build 10920"

opt pagewidth 120

	opt pm

	processor	16F1938
clrc	macro
	bcf	3,0
	endm
clrz	macro
	bcf	3,2
	endm
setc	macro
	bsf	3,0
	endm
setz	macro
	bsf	3,2
	endm
skipc	macro
	btfss	3,0
	endm
skipz	macro
	btfss	3,2
	endm
skipnc	macro
	btfsc	3,0
	endm
skipnz	macro
	btfsc	3,2
	endm
indf	equ	0
indf0	equ	0
indf1	equ	1
pc	equ	2
pcl	equ	2
status	equ	3
fsr0l	equ	4
fsr0h	equ	5
fsr1l	equ	6
fsr1h	equ	7
bsr	equ	8
wreg	equ	9
intcon	equ	11
c	equ	1
z	equ	0
pclath	equ	10
	FNCALL	_main,_POWER_INITIAL
	FNCALL	_main,_IO_INT_INITIAL
	FNROOT	_main
	FNCALL	intlevel1,_ISR
	global	intlevel1
	FNROOT	intlevel1
	global	_EPIF0
psect	intentry,class=CODE,delta=2
global __pintentry
__pintentry:
_EPIF0	set	20
	global	_INTCON
_INTCON	set	11
	global	_PORTA
_PORTA	set	12
	global	_PORTB
_PORTB	set	13
	global	_PORTC
_PORTC	set	14
	global	_PB3
_PB3	set	107
	global	_EPIE0
_EPIE0	set	148
	global	_OSCCON
_OSCCON	set	153
	global	_TRISA
_TRISA	set	140
	global	_TRISB
_TRISB	set	141
	global	_TRISC
_TRISC	set	142
	global	_EPS0
_EPS0	set	280
	global	_EPS1
_EPS1	set	281
	global	_ITYPE0
_ITYPE0	set	286
	global	_ITYPE1
_ITYPE1	set	287
	global	_PSRC0
_PSRC0	set	282
	global	_PSRC1
_PSRC1	set	283
	global	_ANSELA
_ANSELA	set	407
	global	_PSINK0
_PSINK0	set	410
	global	_PSINK1
_PSINK1	set	411
	global	_PSINK2
_PSINK2	set	412
	global	_WPUA
_WPUA	set	396
	global	_WPUB
_WPUB	set	397
	global	_WPUC
_WPUC	set	398
	global	_WPDA
_WPDA	set	524
	global	_WPDB
_WPDB	set	525
	global	_WPDC
_WPDC	set	526
	file	"test_61f14x_io_interrupt.as"
	line	#
psect cinit,class=CODE,delta=2
global start_initialization
start_initialization:

psect cinit,class=CODE,delta=2
global end_of_initialization

;End of C runtime variable initialization code

end_of_initialization:
movlb 0
ljmp _main	;jump to C main() function
psect	cstackCOMMON,class=COMMON,space=1
global __pcstackCOMMON
__pcstackCOMMON:
	global	?_ISR
?_ISR:	; 0 bytes @ 0x0
	global	??_ISR
??_ISR:	; 0 bytes @ 0x0
	global	?_POWER_INITIAL
?_POWER_INITIAL:	; 0 bytes @ 0x0
	global	??_POWER_INITIAL
??_POWER_INITIAL:	; 0 bytes @ 0x0
	global	?_IO_INT_INITIAL
?_IO_INT_INITIAL:	; 0 bytes @ 0x0
	global	??_IO_INT_INITIAL
??_IO_INT_INITIAL:	; 0 bytes @ 0x0
	global	?_main
?_main:	; 0 bytes @ 0x0
	global	??_main
??_main:	; 0 bytes @ 0x0
;;Data sizes: Strings 0, constant 0, data 0, bss 0, persistent 0 stack 0
;;Auto spaces:   Size  Autos    Used
;; COMMON          14      0       0
;; BANK0           80      0       0
;; BANK1           80      0       0
;; BANK2           80      0       0
;; BANK3           80      0       0
;; BANK4           80      0       0
;; BANK5           80      0       0
;; BANK6           16      0       0

;;
;; Pointer list with targets:



;;
;; Critical Paths under _main in COMMON
;;
;;   None.
;;
;; Critical Paths under _ISR in COMMON
;;
;;   None.
;;
;; Critical Paths under _main in BANK0
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK0
;;
;;   None.
;;
;; Critical Paths under _main in BANK1
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK1
;;
;;   None.
;;
;; Critical Paths under _main in BANK2
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK2
;;
;;   None.
;;
;; Critical Paths under _main in BANK3
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK3
;;
;;   None.
;;
;; Critical Paths under _main in BANK4
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK4
;;
;;   None.
;;
;; Critical Paths under _main in BANK5
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK5
;;
;;   None.
;;
;; Critical Paths under _main in BANK6
;;
;;   None.
;;
;; Critical Paths under _ISR in BANK6
;;
;;   None.

;;
;;Main: autosize = 0, tempsize = 0, incstack = 0, save=0
;;

;;
;;Call Graph Tables:
;;
;; ---------------------------------------------------------------------------------
;; (Depth) Function   	        Calls       Base Space   Used Autos Params    Refs
;; ---------------------------------------------------------------------------------
;; (0) _main                                                 0     0      0       0
;;                      _POWER_INITIAL
;;                     _IO_INT_INITIAL
;; ---------------------------------------------------------------------------------
;; (1) _IO_INT_INITIAL                                       0     0      0       0
;; ---------------------------------------------------------------------------------
;; (1) _POWER_INITIAL                                        0     0      0       0
;; ---------------------------------------------------------------------------------
;; Estimated maximum stack depth 1
;; ---------------------------------------------------------------------------------
;; (Depth) Function   	        Calls       Base Space   Used Autos Params    Refs
;; ---------------------------------------------------------------------------------
;; (2) _ISR                                                  0     0      0       0
;; ---------------------------------------------------------------------------------
;; Estimated maximum stack depth 2
;; ---------------------------------------------------------------------------------

;; Call Graph Graphs:

;; _main (ROOT)
;;   _POWER_INITIAL
;;   _IO_INT_INITIAL
;;
;; _ISR (ROOT)
;;

;; Address spaces:

;;Name               Size   Autos  Total    Cost      Usage
;;BIGRAM             1F0      0       0       0        0.0%
;;EEDATA              80      0       0       0        0.0%
;;NULL                 0      0       0       0        0.0%
;;CODE                 0      0       0       0        0.0%
;;BITCOMMON            E      0       0       1        0.0%
;;BITSFR0              0      0       0       1        0.0%
;;SFR0                 0      0       0       1        0.0%
;;COMMON               E      0       0       2        0.0%
;;BITSFR1              0      0       0       2        0.0%
;;SFR1                 0      0       0       2        0.0%
;;BITSFR2              0      0       0       3        0.0%
;;SFR2                 0      0       0       3        0.0%
;;STACK                0      0       1       3        0.0%
;;BITSFR3              0      0       0       4        0.0%
;;SFR3                 0      0       0       4        0.0%
;;ABS                  0      0       0       4        0.0%
;;BITBANK0            50      0       0       5        0.0%
;;BITSFR4              0      0       0       5        0.0%
;;SFR4                 0      0       0       5        0.0%
;;BANK0               50      0       0       6        0.0%
;;BITSFR5              0      0       0       6        0.0%
;;SFR5                 0      0       0       6        0.0%
;;BITBANK1            50      0       0       7        0.0%
;;BITSFR6              0      0       0       7        0.0%
;;SFR6                 0      0       0       7        0.0%
;;BANK1               50      0       0       8        0.0%
;;BITSFR7              0      0       0       8        0.0%
;;SFR7                 0      0       0       8        0.0%
;;BITBANK2            50      0       0       9        0.0%
;;BITSFR8              0      0       0       9        0.0%
;;SFR8                 0      0       0       9        0.0%
;;BANK2               50      0       0      10        0.0%
;;BITSFR9              0      0       0      10        0.0%
;;SFR9                 0      0       0      10        0.0%
;;BITBANK3            50      0       0      11        0.0%
;;BITSFR10             0      0       0      11        0.0%
;;SFR10                0      0       0      11        0.0%
;;BANK3               50      0       0      12        0.0%
;;BITSFR11             0      0       0      12        0.0%
;;SFR11                0      0       0      12        0.0%
;;BITBANK4            50      0       0      13        0.0%
;;BITSFR12             0      0       0      13        0.0%
;;SFR12                0      0       0      13        0.0%
;;BANK4               50      0       0      14        0.0%
;;BITSFR13             0      0       0      14        0.0%
;;SFR13                0      0       0      14        0.0%
;;BITBANK5            50      0       0      15        0.0%
;;BITSFR14             0      0       0      15        0.0%
;;SFR14                0      0       0      15        0.0%
;;BANK5               50      0       0      16        0.0%
;;BITSFR15             0      0       0      16        0.0%
;;SFR15                0      0       0      16        0.0%
;;BITBANK6            10      0       0      17        0.0%
;;BITSFR16             0      0       0      17        0.0%
;;SFR16                0      0       0      17        0.0%
;;BANK6               10      0       0      18        0.0%
;;BITSFR17             0      0       0      18        0.0%
;;SFR17                0      0       0      18        0.0%
;;BITSFR18             0      0       0      19        0.0%
;;SFR18                0      0       0      19        0.0%
;;DATA                 0      0       0      19        0.0%
;;BITSFR19             0      0       0      20        0.0%
;;SFR19                0      0       0      20        0.0%
;;BITSFR20             0      0       0      21        0.0%
;;SFR20                0      0       0      21        0.0%
;;BITSFR21             0      0       0      22        0.0%
;;SFR21                0      0       0      22        0.0%
;;BITSFR22             0      0       0      23        0.0%
;;SFR22                0      0       0      23        0.0%
;;BITSFR23             0      0       0      24        0.0%
;;SFR23                0      0       0      24        0.0%
;;BITSFR24             0      0       0      25        0.0%
;;SFR24                0      0       0      25        0.0%
;;BITSFR25             0      0       0      26        0.0%
;;SFR25                0      0       0      26        0.0%
;;BITSFR26             0      0       0      27        0.0%
;;SFR26                0      0       0      27        0.0%
;;BITSFR27             0      0       0      28        0.0%
;;SFR27                0      0       0      28        0.0%
;;BITSFR28             0      0       0      29        0.0%
;;SFR28                0      0       0      29        0.0%
;;BITSFR29             0      0       0      30        0.0%
;;SFR29                0      0       0      30        0.0%
;;BITSFR30             0      0       0      31        0.0%
;;SFR30                0      0       0      31        0.0%
;;BITSFR31             0      0       0      32        0.0%
;;SFR31                0      0       0      32        0.0%

	global	_main
psect	maintext,global,class=CODE,delta=2
global __pmaintext
__pmaintext:

;; *************** function _main *****************
;; Defined at:
;;		line 163 in file "test_61f14x_IO_INTERRUPT.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, status,2, status,0, pclath, cstack
;; Tracked objects:
;;		On entry : 17F/0
;;		On exit  : 0/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         0       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         0       0       0       0       0       0       0       0
;;Total ram usage:        0 bytes
;; Hardware stack levels required when called:    2
;; This function calls:
;;		_POWER_INITIAL
;;		_IO_INT_INITIAL
;; This function is called by:
;;		Startup code after reset
;; This function uses a non-reentrant model
;;
psect	maintext
	file	"test_61f14x_IO_INTERRUPT.C"
	line	163
	global	__size_of_main
	__size_of_main	equ	__end_of_main-_main
	
_main:	
	opt	stack 14
; Regs used in _main: [wreg+status,2+status,0+pclath+cstack]
	line	164
	
l3731:	
;test_61f14x_IO_INTERRUPT.C: 164: POWER_INITIAL();
	fcall	_POWER_INITIAL
	line	165
;test_61f14x_IO_INTERRUPT.C: 165: IO_INT_INITIAL();
	fcall	_IO_INT_INITIAL
	line	169
	
l3733:	
;test_61f14x_IO_INTERRUPT.C: 168: {
;test_61f14x_IO_INTERRUPT.C: 169: _nop();
	nop
	goto	l3733
	global	start
	ljmp	start
	opt stack 0
psect	maintext
	line	171
GLOBAL	__end_of_main
	__end_of_main:
;; =============== function _main ends ============

	signat	_main,88
	global	_IO_INT_INITIAL
psect	text50,local,class=CODE,delta=2
global __ptext50
__ptext50:

;; *************** function _IO_INT_INITIAL *****************
;; Defined at:
;;		line 143 in file "test_61f14x_IO_INTERRUPT.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, status,2
;; Tracked objects:
;;		On entry : 17F/3
;;		On exit  : 17F/1
;;		Unchanged: FFE80/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         0       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         0       0       0       0       0       0       0       0
;;Total ram usage:        0 bytes
;; Hardware stack levels used:    1
;; Hardware stack levels required when called:    1
;; This function calls:
;;		Nothing
;; This function is called by:
;;		_main
;; This function uses a non-reentrant model
;;
psect	text50
	file	"test_61f14x_IO_INTERRUPT.C"
	line	143
	global	__size_of_IO_INT_INITIAL
	__size_of_IO_INT_INITIAL	equ	__end_of_IO_INT_INITIAL-_IO_INT_INITIAL
	
_IO_INT_INITIAL:	
	opt	stack 14
; Regs used in _IO_INT_INITIAL: [wreg+status,2]
	line	144
	
l3721:	
;test_61f14x_IO_INTERRUPT.C: 144: EPS0=0B00001000;
	movlw	(08h)
	movlb 2	; select bank2
	movwf	(280)^0100h	;volatile
	line	146
	
l3723:	
;test_61f14x_IO_INTERRUPT.C: 146: EPS1=0B00000000;
	clrf	(281)^0100h	;volatile
	line	149
	
l3725:	
;test_61f14x_IO_INTERRUPT.C: 149: ITYPE0 = 0B00001100;
	movlw	(0Ch)
	movwf	(286)^0100h	;volatile
	line	150
;test_61f14x_IO_INTERRUPT.C: 150: ITYPE1 = 0B00000000;
	clrf	(287)^0100h	;volatile
	line	152
	
l3727:	
;test_61f14x_IO_INTERRUPT.C: 152: EPIE0 = 0B00000010;
	movlw	(02h)
	movlb 1	; select bank1
	movwf	(148)^080h	;volatile
	line	154
	
l3729:	
;test_61f14x_IO_INTERRUPT.C: 154: INTCON = 0B11000000;
	movlw	(0C0h)
	movwf	(11)	;volatile
	line	155
	
l1624:	
	return
	opt stack 0
GLOBAL	__end_of_IO_INT_INITIAL
	__end_of_IO_INT_INITIAL:
;; =============== function _IO_INT_INITIAL ends ============

	signat	_IO_INT_INITIAL,88
	global	_POWER_INITIAL
psect	text51,local,class=CODE,delta=2
global __ptext51
__ptext51:

;; *************** function _POWER_INITIAL *****************
;; Defined at:
;;		line 59 in file "test_61f14x_IO_INTERRUPT.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, status,2
;; Tracked objects:
;;		On entry : 17F/0
;;		On exit  : 17F/3
;;		Unchanged: FFE80/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         0       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         0       0       0       0       0       0       0       0
;;Total ram usage:        0 bytes
;; Hardware stack levels used:    1
;; Hardware stack levels required when called:    1
;; This function calls:
;;		Nothing
;; This function is called by:
;;		_main
;; This function uses a non-reentrant model
;;
psect	text51
	file	"test_61f14x_IO_INTERRUPT.C"
	line	59
	global	__size_of_POWER_INITIAL
	__size_of_POWER_INITIAL	equ	__end_of_POWER_INITIAL-_POWER_INITIAL
	
_POWER_INITIAL:	
	opt	stack 14
; Regs used in _POWER_INITIAL: [wreg+status,2]
	line	60
	
l3687:	
;test_61f14x_IO_INTERRUPT.C: 60: OSCCON = 0B01110001;
	movlw	(071h)
	movlb 1	; select bank1
	movwf	(153)^080h	;volatile
	line	61
	
l3689:	
;test_61f14x_IO_INTERRUPT.C: 61: INTCON = 0;
	clrf	(11)	;volatile
	line	63
	
l3691:	
;test_61f14x_IO_INTERRUPT.C: 63: PORTA = 0B00000000;
	movlb 0	; select bank0
	clrf	(12)	;volatile
	line	64
	
l3693:	
;test_61f14x_IO_INTERRUPT.C: 64: TRISA = 0B00000000;
	movlb 1	; select bank1
	clrf	(140)^080h	;volatile
	line	65
	
l3695:	
;test_61f14x_IO_INTERRUPT.C: 65: PORTB = 0B00000000;
	movlb 0	; select bank0
	clrf	(13)	;volatile
	line	66
	
l3697:	
;test_61f14x_IO_INTERRUPT.C: 66: TRISB = 0B00000000;
	movlb 1	; select bank1
	clrf	(141)^080h	;volatile
	line	67
	
l3699:	
;test_61f14x_IO_INTERRUPT.C: 67: PORTC = 0B00000000;
	movlb 0	; select bank0
	clrf	(14)	;volatile
	line	68
;test_61f14x_IO_INTERRUPT.C: 68: TRISC = 0B00000010;
	movlw	(02h)
	movlb 1	; select bank1
	movwf	(142)^080h	;volatile
	line	71
	
l3701:	
;test_61f14x_IO_INTERRUPT.C: 71: WPUA = 0B00000000;
	movlb 3	; select bank3
	clrf	(396)^0180h	;volatile
	line	72
	
l3703:	
;test_61f14x_IO_INTERRUPT.C: 72: WPUB = 0B00000000;
	clrf	(397)^0180h	;volatile
	line	73
;test_61f14x_IO_INTERRUPT.C: 73: WPUC = 0B00000010;
	movlw	(02h)
	movwf	(398)^0180h	;volatile
	line	75
	
l3705:	
;test_61f14x_IO_INTERRUPT.C: 75: WPDA = 0B00000000;
	movlb 4	; select bank4
	clrf	(524)^0200h	;volatile
	line	76
	
l3707:	
;test_61f14x_IO_INTERRUPT.C: 76: WPDB = 0B00000000;
	clrf	(525)^0200h	;volatile
	line	77
	
l3709:	
;test_61f14x_IO_INTERRUPT.C: 77: WPDC = 0B00000000;
	clrf	(526)^0200h	;volatile
	line	79
	
l3711:	
;test_61f14x_IO_INTERRUPT.C: 79: PSRC0 = 0B11111111;
	movlw	(0FFh)
	movlb 2	; select bank2
	movwf	(282)^0100h	;volatile
	line	80
	
l3713:	
;test_61f14x_IO_INTERRUPT.C: 80: PSRC1 = 0B11111111;
	movlw	(0FFh)
	movwf	(283)^0100h	;volatile
	line	82
	
l3715:	
;test_61f14x_IO_INTERRUPT.C: 82: PSINK0 = 0B11111111;
	movlw	(0FFh)
	movlb 3	; select bank3
	movwf	(410)^0180h	;volatile
	line	83
	
l3717:	
;test_61f14x_IO_INTERRUPT.C: 83: PSINK1 = 0B11111111;
	movlw	(0FFh)
	movwf	(411)^0180h	;volatile
	line	84
	
l3719:	
;test_61f14x_IO_INTERRUPT.C: 84: PSINK2 = 0B11111111;
	movlw	(0FFh)
	movwf	(412)^0180h	;volatile
	line	86
;test_61f14x_IO_INTERRUPT.C: 86: ANSELA = 0B00000000;
	clrf	(407)^0180h	;volatile
	line	87
	
l1599:	
	return
	opt stack 0
GLOBAL	__end_of_POWER_INITIAL
	__end_of_POWER_INITIAL:
;; =============== function _POWER_INITIAL ends ============

	signat	_POWER_INITIAL,88
	global	_ISR
psect	intentry

;; *************** function _ISR *****************
;; Defined at:
;;		line 38 in file "test_61f14x_IO_INTERRUPT.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg
;; Tracked objects:
;;		On entry : 0/0
;;		On exit  : 1F/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         0       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         0       0       0       0       0       0       0       0
;;Total ram usage:        0 bytes
;; Hardware stack levels used:    1
;; This function calls:
;;		Nothing
;; This function is called by:
;;		Interrupt level 1
;; This function uses a non-reentrant model
;;
psect	intentry
	file	"test_61f14x_IO_INTERRUPT.C"
	line	38
	global	__size_of_ISR
	__size_of_ISR	equ	__end_of_ISR-_ISR
	
_ISR:	
	opt	stack 14
; Regs used in _ISR: [wreg]
psect	intentry
	pagesel	$
	line	39
	
i1l3669:	
;test_61f14x_IO_INTERRUPT.C: 39: if(EPIF0 & 0x02)
	movlb 0	; select bank0
	btfss	(20),(1)&7
	goto	u1_21
	goto	u1_20
u1_21:
	goto	i1l1596
u1_20:
	line	41
	
i1l3671:	
;test_61f14x_IO_INTERRUPT.C: 40: {
;test_61f14x_IO_INTERRUPT.C: 41: EPIF0 = 0x02;
	movlw	(02h)
	movwf	(20)	;volatile
	line	43
	
i1l3673:	
;test_61f14x_IO_INTERRUPT.C: 43: PB3=1;
	bsf	(107/8),(107)&7
	line	44
	
i1l3675:	
;test_61f14x_IO_INTERRUPT.C: 44: _nop();
	nop
	line	45
	
i1l3677:	
;test_61f14x_IO_INTERRUPT.C: 45: _nop();
	nop
	line	46
	
i1l3679:	
;test_61f14x_IO_INTERRUPT.C: 46: _nop();
	nop
	line	47
	
i1l3681:	
;test_61f14x_IO_INTERRUPT.C: 47: _nop();
	nop
	line	48
	
i1l3683:	
;test_61f14x_IO_INTERRUPT.C: 48: _nop();
	nop
	line	49
	
i1l3685:	
;test_61f14x_IO_INTERRUPT.C: 49: PB3=0;
	movlb 0	; select bank0
	bcf	(107/8),(107)&7
	line	51
	
i1l1596:	
	retfie
	opt stack 0
GLOBAL	__end_of_ISR
	__end_of_ISR:
;; =============== function _ISR ends ============

	signat	_ISR,88
psect	intentry
	global	btemp
	btemp set 07Eh

	DABS	1,126,2	;btemp
	global	wtemp0
	wtemp0 set btemp
	end
