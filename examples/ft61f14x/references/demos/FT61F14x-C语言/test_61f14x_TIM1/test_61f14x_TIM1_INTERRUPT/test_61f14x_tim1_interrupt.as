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
	FNCALL	_main,_Time1Initial
	FNROOT	_main
	FNCALL	intlevel1,_ISR
	global	intlevel1
	FNROOT	intlevel1
	global	_INTCON
psect	intentry,class=CODE,delta=2
global __pintentry
__pintentry:
_INTCON	set	11
	global	_PORTA
_PORTA	set	12
	global	_PORTB
_PORTB	set	13
	global	_PORTC
_PORTC	set	14
	global	_GIE
_GIE	set	95
	global	_PA0
_PA0	set	96
	global	_PA1
_PA1	set	97
	global	_CKOCON
_CKOCON	set	149
	global	_OSCCON
_OSCCON	set	153
	global	_PCKEN
_PCKEN	set	154
	global	_TRISA
_TRISA	set	140
	global	_TRISB
_TRISB	set	141
	global	_TRISC
_TRISC	set	142
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
	global	_TIM1CR1
_TIM1CR1	set	529
	global	_TIM1IER
_TIM1IER	set	533
	global	_WPDA
_WPDA	set	524
	global	_WPDB
_WPDB	set	525
	global	_WPDC
_WPDC	set	526
	global	_T1UIE
_T1UIE	set	4264
	global	_T1UIF
_T1UIF	set	4272
	global	_TIM1ARRH
_TIM1ARRH	set	656
	global	_TIM1ARRL
_TIM1ARRL	set	657
	global	_TCKSRC
_TCKSRC	set	799
	file	"test_61f14x_tim1_interrupt.as"
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
	global	?_Time1Initial
?_Time1Initial:	; 0 bytes @ 0x0
	global	??_Time1Initial
??_Time1Initial:	; 0 bytes @ 0x0
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
;;                       _Time1Initial
;; ---------------------------------------------------------------------------------
;; (1) _Time1Initial                                         0     0      0       0
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
;;   _Time1Initial
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
;;		line 198 in file "test_61f14x_TIM1_INTERRUPT.C"
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
;;		_Time1Initial
;; This function is called by:
;;		Startup code after reset
;; This function uses a non-reentrant model
;;
psect	maintext
	file	"test_61f14x_TIM1_INTERRUPT.C"
	line	198
	global	__size_of_main
	__size_of_main	equ	__end_of_main-_main
	
_main:	
	opt	stack 14
; Regs used in _main: [wreg+status,2+status,0+pclath+cstack]
	line	199
	
l3689:	
;test_61f14x_TIM1_INTERRUPT.C: 199: POWER_INITIAL();
	fcall	_POWER_INITIAL
	line	200
;test_61f14x_TIM1_INTERRUPT.C: 200: Time1Initial();
	fcall	_Time1Initial
	line	204
	
l3691:	
;test_61f14x_TIM1_INTERRUPT.C: 203: {
;test_61f14x_TIM1_INTERRUPT.C: 204: _nop();
	nop
	goto	l3691
	global	start
	ljmp	start
	opt stack 0
psect	maintext
	line	206
GLOBAL	__end_of_main
	__end_of_main:
;; =============== function _main ends ============

	signat	_main,88
	global	_Time1Initial
psect	text50,local,class=CODE,delta=2
global __ptext50
__ptext50:

;; *************** function _Time1Initial *****************
;; Defined at:
;;		line 84 in file "test_61f14x_TIM1_INTERRUPT.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg
;; Tracked objects:
;;		On entry : 17F/3
;;		On exit  : 17F/5
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
	file	"test_61f14x_TIM1_INTERRUPT.C"
	line	84
	global	__size_of_Time1Initial
	__size_of_Time1Initial	equ	__end_of_Time1Initial-_Time1Initial
	
_Time1Initial:	
	opt	stack 14
; Regs used in _Time1Initial: [wreg]
	line	85
	
l3683:	
;test_61f14x_TIM1_INTERRUPT.C: 85: PCKEN |=0B00000010;
	movlb 1	; select bank1
	bsf	(154)^080h+(1/8),(1)&7	;volatile
	line	86
	
l3685:	
;test_61f14x_TIM1_INTERRUPT.C: 86: CKOCON=0B00100000;
	movlw	(020h)
	movwf	(149)^080h	;volatile
	line	87
;test_61f14x_TIM1_INTERRUPT.C: 87: TCKSRC=0B00000011;
	movlw	(03h)
	movlb 6	; select bank6
	movwf	(799)^0300h	;volatile
	line	114
;test_61f14x_TIM1_INTERRUPT.C: 114: TIM1CR1 =0B10000101;
	movlw	(085h)
	movlb 4	; select bank4
	movwf	(529)^0200h	;volatile
	line	153
;test_61f14x_TIM1_INTERRUPT.C: 153: TIM1IER =0B00000001;
	movlw	(01h)
	movwf	(533)^0200h	;volatile
	line	186
;test_61f14x_TIM1_INTERRUPT.C: 186: TIM1ARRH =0x03;
	movlw	(03h)
	movlb 5	; select bank5
	movwf	(656)^0280h	;volatile
	line	187
;test_61f14x_TIM1_INTERRUPT.C: 187: TIM1ARRL =0xe8;
	movlw	(0E8h)
	movwf	(657)^0280h	;volatile
	line	189
	
l3687:	
;test_61f14x_TIM1_INTERRUPT.C: 189: GIE=1;
	bsf	(95/8),(95)&7
	line	190
	
l1602:	
	return
	opt stack 0
GLOBAL	__end_of_Time1Initial
	__end_of_Time1Initial:
;; =============== function _Time1Initial ends ============

	signat	_Time1Initial,88
	global	_POWER_INITIAL
psect	text51,local,class=CODE,delta=2
global __ptext51
__ptext51:

;; *************** function _POWER_INITIAL *****************
;; Defined at:
;;		line 49 in file "test_61f14x_TIM1_INTERRUPT.C"
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
	file	"test_61f14x_TIM1_INTERRUPT.C"
	line	49
	global	__size_of_POWER_INITIAL
	__size_of_POWER_INITIAL	equ	__end_of_POWER_INITIAL-_POWER_INITIAL
	
_POWER_INITIAL:	
	opt	stack 14
; Regs used in _POWER_INITIAL: [wreg+status,2]
	line	50
	
l3655:	
;test_61f14x_TIM1_INTERRUPT.C: 50: OSCCON = 0B01110001;
	movlw	(071h)
	movlb 1	; select bank1
	movwf	(153)^080h	;volatile
	line	51
;test_61f14x_TIM1_INTERRUPT.C: 51: INTCON = 0B01000000;
	movlw	(040h)
	movwf	(11)	;volatile
	line	53
	
l3657:	
;test_61f14x_TIM1_INTERRUPT.C: 53: PORTA = 0B00000000;
	movlb 0	; select bank0
	clrf	(12)	;volatile
	line	54
	
l3659:	
;test_61f14x_TIM1_INTERRUPT.C: 54: TRISA = 0B00000000;
	movlb 1	; select bank1
	clrf	(140)^080h	;volatile
	line	55
	
l3661:	
;test_61f14x_TIM1_INTERRUPT.C: 55: PORTB = 0B00000000;
	movlb 0	; select bank0
	clrf	(13)	;volatile
	line	56
	
l3663:	
;test_61f14x_TIM1_INTERRUPT.C: 56: TRISB = 0B00000000;
	movlb 1	; select bank1
	clrf	(141)^080h	;volatile
	line	57
	
l3665:	
;test_61f14x_TIM1_INTERRUPT.C: 57: PORTC = 0B00000000;
	movlb 0	; select bank0
	clrf	(14)	;volatile
	line	58
	
l3667:	
;test_61f14x_TIM1_INTERRUPT.C: 58: TRISC = 0B00000000;
	movlb 1	; select bank1
	clrf	(142)^080h	;volatile
	line	60
	
l3669:	
;test_61f14x_TIM1_INTERRUPT.C: 60: WPUA = 0B00000000;
	movlb 3	; select bank3
	clrf	(396)^0180h	;volatile
	line	61
	
l3671:	
;test_61f14x_TIM1_INTERRUPT.C: 61: WPUB = 0B00000000;
	clrf	(397)^0180h	;volatile
	line	62
	
l3673:	
;test_61f14x_TIM1_INTERRUPT.C: 62: WPUC = 0B00000000;
	clrf	(398)^0180h	;volatile
	line	64
	
l3675:	
;test_61f14x_TIM1_INTERRUPT.C: 64: WPDA = 0B00000000;
	movlb 4	; select bank4
	clrf	(524)^0200h	;volatile
	line	65
	
l3677:	
;test_61f14x_TIM1_INTERRUPT.C: 65: WPDB = 0B00000000;
	clrf	(525)^0200h	;volatile
	line	66
	
l3679:	
;test_61f14x_TIM1_INTERRUPT.C: 66: WPDC = 0B00000000;
	clrf	(526)^0200h	;volatile
	line	68
;test_61f14x_TIM1_INTERRUPT.C: 68: PSRC0 = 0B11111111;
	movlw	(0FFh)
	movlb 2	; select bank2
	movwf	(282)^0100h	;volatile
	line	69
;test_61f14x_TIM1_INTERRUPT.C: 69: PSRC1 = 0B11111111;
	movlw	(0FFh)
	movwf	(283)^0100h	;volatile
	line	71
;test_61f14x_TIM1_INTERRUPT.C: 71: PSINK0 = 0B11111111;
	movlw	(0FFh)
	movlb 3	; select bank3
	movwf	(410)^0180h	;volatile
	line	72
;test_61f14x_TIM1_INTERRUPT.C: 72: PSINK1 = 0B11111111;
	movlw	(0FFh)
	movwf	(411)^0180h	;volatile
	line	73
;test_61f14x_TIM1_INTERRUPT.C: 73: PSINK2 = 0B11111111;
	movlw	(0FFh)
	movwf	(412)^0180h	;volatile
	line	75
	
l3681:	
;test_61f14x_TIM1_INTERRUPT.C: 75: ANSELA = 0B00000000;
	clrf	(407)^0180h	;volatile
	line	76
	
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
;;		line 33 in file "test_61f14x_TIM1_INTERRUPT.C"
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
;;		On exit  : 1B/0
;;		Unchanged: FFFE0/0
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
	file	"test_61f14x_TIM1_INTERRUPT.C"
	line	33
	global	__size_of_ISR
	__size_of_ISR	equ	__end_of_ISR-_ISR
	
_ISR:	
	opt	stack 14
; Regs used in _ISR: [wreg]
psect	intentry
	pagesel	$
	line	34
	
i1l3647:	
;test_61f14x_TIM1_INTERRUPT.C: 34: if(T1UIE && T1UIF)
	movlb 4	; select bank4
	btfss	(4264/8)^0200h,(4264)&7
	goto	u1_21
	goto	u1_20
u1_21:
	goto	i1l1596
u1_20:
	
i1l3649:	
	btfss	(4272/8)^0200h,(4272)&7
	goto	u2_21
	goto	u2_20
u2_21:
	goto	i1l1596
u2_20:
	line	36
	
i1l3651:	
;test_61f14x_TIM1_INTERRUPT.C: 35: {
;test_61f14x_TIM1_INTERRUPT.C: 36: T1UIF = 1;
	bsf	(4272/8)^0200h,(4272)&7
	line	37
	
i1l3653:	
;test_61f14x_TIM1_INTERRUPT.C: 37: PA1 = ~PA1;
	movlw	1<<((97)&7)
	movlb 0	; select bank0
	xorwf	((97)/8),f
	line	38
;test_61f14x_TIM1_INTERRUPT.C: 38: PA0 = !PA0;
	movlw	1<<((96)&7)
	xorwf	((96)/8),f
	line	40
	
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
