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
	FNCALL	_main,_WDT_INITIAL
	FNCALL	_main,_DelayMs
	FNCALL	_DelayMs,_DelayUs
	FNROOT	_main
	global	_INTCON
psect	text58,local,class=CODE,delta=2
global __ptext58
__ptext58:
_INTCON	set	11
	global	_PORTA
_PORTA	set	12
	global	_PORTB
_PORTB	set	13
	global	_PORTC
_PORTC	set	14
	global	_PA0
_PA0	set	96
	global	_OSCCON
_OSCCON	set	153
	global	_TRISA
_TRISA	set	140
	global	_TRISB
_TRISB	set	141
	global	_TRISC
_TRISC	set	142
	global	_WDTCON
_WDTCON	set	151
	global	_PSRC0
_PSRC0	set	282
	global	_PSRC1
_PSRC1	set	283
	global	_ANSELA
_ANSELA	set	407
	global	_MISC0
_MISC0	set	413
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
	file	"test_61f14x_wdt.as"
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
	global	?_POWER_INITIAL
?_POWER_INITIAL:	; 0 bytes @ 0x0
	global	??_POWER_INITIAL
??_POWER_INITIAL:	; 0 bytes @ 0x0
	global	?_DelayUs
?_DelayUs:	; 0 bytes @ 0x0
	global	??_DelayUs
??_DelayUs:	; 0 bytes @ 0x0
	global	?_DelayMs
?_DelayMs:	; 0 bytes @ 0x0
	global	?_WDT_INITIAL
?_WDT_INITIAL:	; 0 bytes @ 0x0
	global	??_WDT_INITIAL
??_WDT_INITIAL:	; 0 bytes @ 0x0
	global	?_main
?_main:	; 0 bytes @ 0x0
	global	DelayUs@Time
DelayUs@Time:	; 1 bytes @ 0x0
	ds	1
	global	DelayUs@a
DelayUs@a:	; 1 bytes @ 0x1
	ds	1
	global	??_DelayMs
??_DelayMs:	; 0 bytes @ 0x2
	global	DelayMs@Time
DelayMs@Time:	; 1 bytes @ 0x2
	ds	1
	global	DelayMs@a
DelayMs@a:	; 1 bytes @ 0x3
	ds	1
	global	DelayMs@b
DelayMs@b:	; 1 bytes @ 0x4
	ds	1
	global	??_main
??_main:	; 0 bytes @ 0x5
;;Data sizes: Strings 0, constant 0, data 0, bss 0, persistent 0 stack 0
;;Auto spaces:   Size  Autos    Used
;; COMMON          14      5       5
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
;;   _main->_DelayMs
;;   _DelayMs->_DelayUs
;;
;; Critical Paths under _main in BANK0
;;
;;   None.
;;
;; Critical Paths under _main in BANK1
;;
;;   None.
;;
;; Critical Paths under _main in BANK2
;;
;;   None.
;;
;; Critical Paths under _main in BANK3
;;
;;   None.
;;
;; Critical Paths under _main in BANK4
;;
;;   None.
;;
;; Critical Paths under _main in BANK5
;;
;;   None.
;;
;; Critical Paths under _main in BANK6
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
;; (0) _main                                                 0     0      0      90
;;                      _POWER_INITIAL
;;                        _WDT_INITIAL
;;                            _DelayMs
;; ---------------------------------------------------------------------------------
;; (1) _DelayMs                                              3     3      0      90
;;                                              2 COMMON     3     3      0
;;                            _DelayUs
;; ---------------------------------------------------------------------------------
;; (2) _DelayUs                                              2     2      0      30
;;                                              0 COMMON     2     2      0
;; ---------------------------------------------------------------------------------
;; (1) _WDT_INITIAL                                          0     0      0       0
;; ---------------------------------------------------------------------------------
;; (1) _POWER_INITIAL                                        0     0      0       0
;; ---------------------------------------------------------------------------------
;; Estimated maximum stack depth 2
;; ---------------------------------------------------------------------------------

;; Call Graph Graphs:

;; _main (ROOT)
;;   _POWER_INITIAL
;;   _WDT_INITIAL
;;   _DelayMs
;;     _DelayUs
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
;;COMMON               E      5       5       2       35.7%
;;BITSFR1              0      0       0       2        0.0%
;;SFR1                 0      0       0       2        0.0%
;;BITSFR2              0      0       0       3        0.0%
;;SFR2                 0      0       0       3        0.0%
;;STACK                0      0       2       3        0.0%
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
;;		line 116 in file "test_61f14x_WDT.C"
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
;;		_WDT_INITIAL
;;		_DelayMs
;; This function is called by:
;;		Startup code after reset
;; This function uses a non-reentrant model
;;
psect	maintext
	file	"test_61f14x_WDT.C"
	line	116
	global	__size_of_main
	__size_of_main	equ	__end_of_main-_main
	
_main:	
	opt	stack 14
; Regs used in _main: [wreg+status,2+status,0+pclath+cstack]
	line	117
	
l3725:	
;test_61f14x_WDT.C: 117: POWER_INITIAL();
	fcall	_POWER_INITIAL
	line	118
;test_61f14x_WDT.C: 118: WDT_INITIAL();
	fcall	_WDT_INITIAL
	line	119
	
l3727:	
;test_61f14x_WDT.C: 119: INTCON = 0B11000000;
	movlw	(0C0h)
	movwf	(11)	;volatile
	line	120
	
l3729:	
;test_61f14x_WDT.C: 120: PA0 = 1;
	movlb 0	; select bank0
	bsf	(96/8),(96)&7
	line	121
	
l3731:	
;test_61f14x_WDT.C: 121: DelayMs(3);
	movlw	(03h)
	fcall	_DelayMs
	line	122
	
l3733:	
;test_61f14x_WDT.C: 122: PA0 = 0;
	movlb 0	; select bank0
	bcf	(96/8),(96)&7
	line	123
	
l3735:	
;test_61f14x_WDT.C: 123: DelayMs(3);
	movlw	(03h)
	fcall	_DelayMs
	line	127
	
l3737:	
;test_61f14x_WDT.C: 125: {
;test_61f14x_WDT.C: 127: PA0 = 1;
	movlb 0	; select bank0
	bsf	(96/8),(96)&7
	line	128
	
l3739:	
;test_61f14x_WDT.C: 128: DelayMs(1);
	movlw	(01h)
	fcall	_DelayMs
	line	129
	
l3741:	
;test_61f14x_WDT.C: 129: PA0 = 0;
	movlb 0	; select bank0
	bcf	(96/8),(96)&7
	line	130
	
l3743:	
;test_61f14x_WDT.C: 130: DelayMs(1);
	movlw	(01h)
	fcall	_DelayMs
	goto	l3737
	global	start
	ljmp	start
	opt stack 0
psect	maintext
	line	132
GLOBAL	__end_of_main
	__end_of_main:
;; =============== function _main ends ============

	signat	_main,88
	global	_DelayMs
psect	text59,local,class=CODE,delta=2
global __ptext59
__ptext59:

;; *************** function _DelayMs *****************
;; Defined at:
;;		line 87 in file "test_61f14x_WDT.C"
;; Parameters:    Size  Location     Type
;;  Time            1    wreg     unsigned char 
;; Auto vars:     Size  Location     Type
;;  Time            1    2[COMMON] unsigned char 
;;  b               1    4[COMMON] unsigned char 
;;  a               1    3[COMMON] unsigned char 
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, status,2, status,0, pclath, cstack
;; Tracked objects:
;;		On entry : 1F/0
;;		On exit  : 0/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         3       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         3       0       0       0       0       0       0       0
;;Total ram usage:        3 bytes
;; Hardware stack levels used:    1
;; Hardware stack levels required when called:    1
;; This function calls:
;;		_DelayUs
;; This function is called by:
;;		_main
;; This function uses a non-reentrant model
;;
psect	text59
	file	"test_61f14x_WDT.C"
	line	87
	global	__size_of_DelayMs
	__size_of_DelayMs	equ	__end_of_DelayMs-_DelayMs
	
_DelayMs:	
	opt	stack 14
; Regs used in _DelayMs: [wreg+status,2+status,0+pclath+cstack]
;DelayMs@Time stored from wreg
	line	89
	movwf	(DelayMs@Time)
	
l3707:	
;test_61f14x_WDT.C: 88: unsigned char a,b;
;test_61f14x_WDT.C: 89: for(a=0;a<Time;a++)
	clrf	(DelayMs@a)
	goto	l3723
	line	91
	
l3709:	
;test_61f14x_WDT.C: 90: {
;test_61f14x_WDT.C: 91: for(b=0;b<5;b++)
	clrf	(DelayMs@b)
	line	93
	
l3715:	
;test_61f14x_WDT.C: 92: {
;test_61f14x_WDT.C: 93: DelayUs(197);
	movlw	(0C5h)
	fcall	_DelayUs
	line	91
	
l3717:	
	incf	(DelayMs@b),f
	
l3719:	
	movlw	(05h)
	subwf	(DelayMs@b),w
	skipc
	goto	u21
	goto	u20
u21:
	goto	l3715
u20:
	line	89
	
l3721:	
	incf	(DelayMs@a),f
	
l3723:	
	movf	(DelayMs@Time),w
	subwf	(DelayMs@a),w
	skipc
	goto	u31
	goto	u30
u31:
	goto	l3709
u30:
	line	96
	
l1609:	
	return
	opt stack 0
GLOBAL	__end_of_DelayMs
	__end_of_DelayMs:
;; =============== function _DelayMs ends ============

	signat	_DelayMs,4216
	global	_DelayUs
psect	text60,local,class=CODE,delta=2
global __ptext60
__ptext60:

;; *************** function _DelayUs *****************
;; Defined at:
;;		line 73 in file "test_61f14x_WDT.C"
;; Parameters:    Size  Location     Type
;;  Time            1    wreg     unsigned char 
;; Auto vars:     Size  Location     Type
;;  Time            1    0[COMMON] unsigned char 
;;  a               1    1[COMMON] unsigned char 
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, status,2, status,0
;; Tracked objects:
;;		On entry : 0/0
;;		On exit  : 0/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         2       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         2       0       0       0       0       0       0       0
;;Total ram usage:        2 bytes
;; Hardware stack levels used:    1
;; This function calls:
;;		Nothing
;; This function is called by:
;;		_DelayMs
;; This function uses a non-reentrant model
;;
psect	text60
	file	"test_61f14x_WDT.C"
	line	73
	global	__size_of_DelayUs
	__size_of_DelayUs	equ	__end_of_DelayUs-_DelayUs
	
_DelayUs:	
	opt	stack 14
; Regs used in _DelayUs: [wreg+status,2+status,0]
;DelayUs@Time stored from wreg
	line	75
	movwf	(DelayUs@Time)
	
l3701:	
;test_61f14x_WDT.C: 74: unsigned char a;
;test_61f14x_WDT.C: 75: for(a=0;a<Time;a++)
	clrf	(DelayUs@a)
	goto	l3705
	line	76
	
l1599:	
	line	77
;test_61f14x_WDT.C: 76: {
;test_61f14x_WDT.C: 77: _nop();
	nop
	line	75
	
l3703:	
	incf	(DelayUs@a),f
	
l3705:	
	movf	(DelayUs@Time),w
	subwf	(DelayUs@a),w
	skipc
	goto	u11
	goto	u10
u11:
	goto	l1599
u10:
	line	79
	
l1601:	
	return
	opt stack 0
GLOBAL	__end_of_DelayUs
	__end_of_DelayUs:
;; =============== function _DelayUs ends ============

	signat	_DelayUs,4216
	global	_WDT_INITIAL
psect	text61,local,class=CODE,delta=2
global __ptext61
__ptext61:

;; *************** function _WDT_INITIAL *****************
;; Defined at:
;;		line 104 in file "test_61f14x_WDT.C"
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
;;		On exit  : 1F/1
;;		Unchanged: FFE00/0
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
;;		_main
;; This function uses a non-reentrant model
;;
psect	text61
	file	"test_61f14x_WDT.C"
	line	104
	global	__size_of_WDT_INITIAL
	__size_of_WDT_INITIAL	equ	__end_of_WDT_INITIAL-_WDT_INITIAL
	
_WDT_INITIAL:	
	opt	stack 15
; Regs used in _WDT_INITIAL: [wreg+status,2]
	line	105
	
l3695:	
# 105 "test_61f14x_WDT.C"
clrwdt ;#
psect	text61
	line	106
	
l3697:	
;test_61f14x_WDT.C: 106: MISC0 = 0B00000000;
	movlb 3	; select bank3
	clrf	(413)^0180h	;volatile
	line	107
	
l3699:	
;test_61f14x_WDT.C: 107: WDTCON = 0B00001011;
	movlw	(0Bh)
	movlb 1	; select bank1
	movwf	(151)^080h	;volatile
	line	108
	
l1612:	
	return
	opt stack 0
GLOBAL	__end_of_WDT_INITIAL
	__end_of_WDT_INITIAL:
;; =============== function _WDT_INITIAL ends ============

	signat	_WDT_INITIAL,88
	global	_POWER_INITIAL
psect	text62,local,class=CODE,delta=2
global __ptext62
__ptext62:

;; *************** function _POWER_INITIAL *****************
;; Defined at:
;;		line 38 in file "test_61f14x_WDT.C"
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
;; This function calls:
;;		Nothing
;; This function is called by:
;;		_main
;; This function uses a non-reentrant model
;;
psect	text62
	file	"test_61f14x_WDT.C"
	line	38
	global	__size_of_POWER_INITIAL
	__size_of_POWER_INITIAL	equ	__end_of_POWER_INITIAL-_POWER_INITIAL
	
_POWER_INITIAL:	
	opt	stack 15
; Regs used in _POWER_INITIAL: [wreg+status,2]
	line	39
	
l3657:	
;test_61f14x_WDT.C: 39: OSCCON = 0B01110001;
	movlw	(071h)
	movlb 1	; select bank1
	movwf	(153)^080h	;volatile
	line	40
	
l3659:	
;test_61f14x_WDT.C: 40: INTCON = 0;
	clrf	(11)	;volatile
	line	42
	
l3661:	
;test_61f14x_WDT.C: 42: PORTA = 0B00000000;
	movlb 0	; select bank0
	clrf	(12)	;volatile
	line	43
	
l3663:	
;test_61f14x_WDT.C: 43: TRISA = 0B00000000;
	movlb 1	; select bank1
	clrf	(140)^080h	;volatile
	line	44
	
l3665:	
;test_61f14x_WDT.C: 44: PORTB = 0B00000000;
	movlb 0	; select bank0
	clrf	(13)	;volatile
	line	45
	
l3667:	
;test_61f14x_WDT.C: 45: TRISB = 0B00000000;
	movlb 1	; select bank1
	clrf	(141)^080h	;volatile
	line	46
	
l3669:	
;test_61f14x_WDT.C: 46: PORTC = 0B00000000;
	movlb 0	; select bank0
	clrf	(14)	;volatile
	line	47
	
l3671:	
;test_61f14x_WDT.C: 47: TRISC = 0B00000000;
	movlb 1	; select bank1
	clrf	(142)^080h	;volatile
	line	49
	
l3673:	
;test_61f14x_WDT.C: 49: WPUA = 0B00000000;
	movlb 3	; select bank3
	clrf	(396)^0180h	;volatile
	line	50
	
l3675:	
;test_61f14x_WDT.C: 50: WPUB = 0B00000000;
	clrf	(397)^0180h	;volatile
	line	51
	
l3677:	
;test_61f14x_WDT.C: 51: WPUC = 0B00000000;
	clrf	(398)^0180h	;volatile
	line	53
	
l3679:	
;test_61f14x_WDT.C: 53: WPDA = 0B00000000;
	movlb 4	; select bank4
	clrf	(524)^0200h	;volatile
	line	54
	
l3681:	
;test_61f14x_WDT.C: 54: WPDB = 0B00000000;
	clrf	(525)^0200h	;volatile
	line	55
	
l3683:	
;test_61f14x_WDT.C: 55: WPDC = 0B00000000;
	clrf	(526)^0200h	;volatile
	line	57
	
l3685:	
;test_61f14x_WDT.C: 57: PSRC0 = 0B11111111;
	movlw	(0FFh)
	movlb 2	; select bank2
	movwf	(282)^0100h	;volatile
	line	58
	
l3687:	
;test_61f14x_WDT.C: 58: PSRC1 = 0B11111111;
	movlw	(0FFh)
	movwf	(283)^0100h	;volatile
	line	60
	
l3689:	
;test_61f14x_WDT.C: 60: PSINK0 = 0B11111111;
	movlw	(0FFh)
	movlb 3	; select bank3
	movwf	(410)^0180h	;volatile
	line	61
	
l3691:	
;test_61f14x_WDT.C: 61: PSINK1 = 0B11111111;
	movlw	(0FFh)
	movwf	(411)^0180h	;volatile
	line	62
	
l3693:	
;test_61f14x_WDT.C: 62: PSINK2 = 0B11111111;
	movlw	(0FFh)
	movwf	(412)^0180h	;volatile
	line	64
;test_61f14x_WDT.C: 64: ANSELA = 0B00000000;
	clrf	(407)^0180h	;volatile
	line	65
	
l1595:	
	return
	opt stack 0
GLOBAL	__end_of_POWER_INITIAL
	__end_of_POWER_INITIAL:
;; =============== function _POWER_INITIAL ends ============

	signat	_POWER_INITIAL,88
psect	text63,local,class=CODE,delta=2
global __ptext63
__ptext63:
	global	btemp
	btemp set 07Eh

	DABS	1,126,2	;btemp
	global	wtemp0
	wtemp0 set btemp
	end
