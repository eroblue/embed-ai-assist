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
	global	_INTCON
psect	text37,local,class=CODE,delta=2
global __ptext37
__ptext37:
_INTCON	set	11
	global	_PORTA
_PORTA	set	12
	global	_PORTB
_PORTB	set	13
	global	_PORTC
_PORTC	set	14
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
	global	_TIM1CCER1
_TIM1CCER1	set	541
	global	_TIM1CCER2
_TIM1CCER2	set	542
	global	_TIM1CCMR1
_TIM1CCMR1	set	537
	global	_TIM1CCMR2
_TIM1CCMR2	set	538
	global	_TIM1CCMR3
_TIM1CCMR3	set	539
	global	_TIM1CCMR4
_TIM1CCMR4	set	540
	global	_TIM1CR1
_TIM1CR1	set	529
	global	_TIM1CR2
_TIM1CR2	set	530
	global	_TIM1EGR
_TIM1EGR	set	536
	global	_TIM1ETR
_TIM1ETR	set	532
	global	_TIM1IER
_TIM1IER	set	533
	global	_TIM1SMCR
_TIM1SMCR	set	531
	global	_TIM1SR1
_TIM1SR1	set	534
	global	_TIM1SR2
_TIM1SR2	set	535
	global	_WPDA
_WPDA	set	524
	global	_WPDB
_WPDB	set	525
	global	_WPDC
_WPDC	set	526
	global	_TIM1ARRH
_TIM1ARRH	set	656
	global	_TIM1ARRL
_TIM1ARRL	set	657
	global	_TIM1BKR
_TIM1BKR	set	667
	global	_TIM1CCR1H
_TIM1CCR1H	set	659
	global	_TIM1CCR1L
_TIM1CCR1L	set	660
	global	_TIM1CNTRH
_TIM1CNTRH	set	652
	global	_TIM1CNTRL
_TIM1CNTRL	set	653
	global	_TIM1DTR
_TIM1DTR	set	668
	global	_TIM1OISR
_TIM1OISR	set	669
	global	_TIM1PSCRH
_TIM1PSCRH	set	654
	global	_TIM1PSCRL
_TIM1PSCRL	set	655
	global	_TIM1RCR
_TIM1RCR	set	658
	global	_TCKSRC
_TCKSRC	set	799
	global	_LEBCON
_LEBCON	set	1052
	file	"test_61f14x_tim1_pwm.as"
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

;; Call Graph Graphs:

;; _main (ROOT)
;;   _POWER_INITIAL
;;   _Time1Initial
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
;;		line 501 in file "test_61f14x_TIM1_PWM.C"
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
;; Hardware stack levels required when called:    1
;; This function calls:
;;		_POWER_INITIAL
;;		_Time1Initial
;; This function is called by:
;;		Startup code after reset
;; This function uses a non-reentrant model
;;
psect	maintext
	file	"test_61f14x_TIM1_PWM.C"
	line	501
	global	__size_of_main
	__size_of_main	equ	__end_of_main-_main
	
_main:	
	opt	stack 15
; Regs used in _main: [wreg+status,2+status,0+pclath+cstack]
	line	502
	
l3717:	
;test_61f14x_TIM1_PWM.C: 502: POWER_INITIAL();
	fcall	_POWER_INITIAL
	line	503
;test_61f14x_TIM1_PWM.C: 503: Time1Initial();
	fcall	_Time1Initial
	line	507
	
l3719:	
;test_61f14x_TIM1_PWM.C: 506: {
;test_61f14x_TIM1_PWM.C: 507: _nop();
	nop
	goto	l3719
	global	start
	ljmp	start
	opt stack 0
psect	maintext
	line	509
GLOBAL	__end_of_main
	__end_of_main:
;; =============== function _main ends ============

	signat	_main,88
	global	_Time1Initial
psect	text38,local,class=CODE,delta=2
global __ptext38
__ptext38:

;; *************** function _Time1Initial *****************
;; Defined at:
;;		line 67 in file "test_61f14x_TIM1_PWM.C"
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
;;		On exit  : 17F/8
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
psect	text38
	file	"test_61f14x_TIM1_PWM.C"
	line	67
	global	__size_of_Time1Initial
	__size_of_Time1Initial	equ	__end_of_Time1Initial-_Time1Initial
	
_Time1Initial:	
	opt	stack 15
; Regs used in _Time1Initial: [wreg+status,2]
	line	68
	
l3681:	
;test_61f14x_TIM1_PWM.C: 68: PCKEN |= 0B00000010;
	movlb 1	; select bank1
	bsf	(154)^080h+(1/8),(1)&7	;volatile
	line	69
	
l3683:	
;test_61f14x_TIM1_PWM.C: 69: CKOCON = 0B00100000;
	movlw	(020h)
	movwf	(149)^080h	;volatile
	line	70
;test_61f14x_TIM1_PWM.C: 70: TCKSRC = 0B00000011;
	movlw	(03h)
	movlb 6	; select bank6
	movwf	(799)^0300h	;volatile
	line	97
;test_61f14x_TIM1_PWM.C: 97: TIM1CR1 =0B10000101;
	movlw	(085h)
	movlb 4	; select bank4
	movwf	(529)^0200h	;volatile
	line	137
	
l3685:	
;test_61f14x_TIM1_PWM.C: 137: TIM1CR2 =0B00000000;
	clrf	(530)^0200h	;volatile
	line	158
	
l3687:	
;test_61f14x_TIM1_PWM.C: 158: TIM1SMCR=0B00000000;
	clrf	(531)^0200h	;volatile
	line	188
	
l3689:	
;test_61f14x_TIM1_PWM.C: 188: TIM1ETR =0B00000000;
	clrf	(532)^0200h	;volatile
	line	227
	
l3691:	
;test_61f14x_TIM1_PWM.C: 227: TIM1IER =0B00000000;
	clrf	(533)^0200h	;volatile
	line	260
	
l3693:	
;test_61f14x_TIM1_PWM.C: 260: TIM1SR1 =0B00000000;
	clrf	(534)^0200h	;volatile
	line	304
	
l3695:	
;test_61f14x_TIM1_PWM.C: 304: TIM1SR2 =0B00000000;
	clrf	(535)^0200h	;volatile
	line	306
	
l3697:	
;test_61f14x_TIM1_PWM.C: 306: TIM1EGR =0B00000000;
	clrf	(536)^0200h	;volatile
	line	343
	
l3699:	
;test_61f14x_TIM1_PWM.C: 343: TIM1CCMR1 =0B01101000;
	movlw	(068h)
	movwf	(537)^0200h	;volatile
	line	385
;test_61f14x_TIM1_PWM.C: 385: TIM1CCMR2 =0B00000000;
	clrf	(538)^0200h	;volatile
	line	386
;test_61f14x_TIM1_PWM.C: 386: TIM1CCMR3 =0B00000000;
	clrf	(539)^0200h	;volatile
	line	387
;test_61f14x_TIM1_PWM.C: 387: TIM1CCMR4 =0B00000000;
	clrf	(540)^0200h	;volatile
	line	389
	
l3701:	
;test_61f14x_TIM1_PWM.C: 389: TIM1CCER1 =0B00001111;
	movlw	(0Fh)
	movwf	(541)^0200h	;volatile
	line	438
	
l3703:	
;test_61f14x_TIM1_PWM.C: 438: TIM1CCER2 =0B00000000;
	clrf	(542)^0200h	;volatile
	line	440
	
l3705:	
;test_61f14x_TIM1_PWM.C: 440: TIM1CNTRH =0B00000000;
	movlb 5	; select bank5
	clrf	(652)^0280h	;volatile
	line	441
	
l3707:	
;test_61f14x_TIM1_PWM.C: 441: TIM1CNTRL =0B00000000;
	clrf	(653)^0280h	;volatile
	line	443
	
l3709:	
;test_61f14x_TIM1_PWM.C: 443: TIM1PSCRH =0B00000000;
	clrf	(654)^0280h	;volatile
	line	444
	
l3711:	
;test_61f14x_TIM1_PWM.C: 444: TIM1PSCRL =0B00000000;
	clrf	(655)^0280h	;volatile
	line	446
;test_61f14x_TIM1_PWM.C: 446: TIM1ARRH =0x03;
	movlw	(03h)
	movwf	(656)^0280h	;volatile
	line	447
;test_61f14x_TIM1_PWM.C: 447: TIM1ARRL =0xe8;
	movlw	(0E8h)
	movwf	(657)^0280h	;volatile
	line	449
;test_61f14x_TIM1_PWM.C: 449: TIM1RCR =0B00001111;
	movlw	(0Fh)
	movwf	(658)^0280h	;volatile
	line	451
;test_61f14x_TIM1_PWM.C: 451: TIM1CCR1H =0x01;
	movlw	(01h)
	movwf	(659)^0280h	;volatile
	line	452
;test_61f14x_TIM1_PWM.C: 452: TIM1CCR1L =0xf4;
	movlw	(0F4h)
	movwf	(660)^0280h	;volatile
	line	454
;test_61f14x_TIM1_PWM.C: 454: TIM1BKR =0B11000000;
	movlw	(0C0h)
	movwf	(667)^0280h	;volatile
	line	455
;test_61f14x_TIM1_PWM.C: 455: TIM1DTR =0B00000111;
	movlw	(07h)
	movwf	(668)^0280h	;volatile
	line	462
	
l3713:	
;test_61f14x_TIM1_PWM.C: 462: TIM1OISR =0B00000000;
	clrf	(669)^0280h	;volatile
	line	472
	
l3715:	
;test_61f14x_TIM1_PWM.C: 472: LEBCON =0B00000000;
	movlb 8	; select bank8
	clrf	(1052)^0400h	;volatile
	line	493
	
l1598:	
	return
	opt stack 0
GLOBAL	__end_of_Time1Initial
	__end_of_Time1Initial:
;; =============== function _Time1Initial ends ============

	signat	_Time1Initial,88
	global	_POWER_INITIAL
psect	text39,local,class=CODE,delta=2
global __ptext39
__ptext39:

;; *************** function _POWER_INITIAL *****************
;; Defined at:
;;		line 31 in file "test_61f14x_TIM1_PWM.C"
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
psect	text39
	file	"test_61f14x_TIM1_PWM.C"
	line	31
	global	__size_of_POWER_INITIAL
	__size_of_POWER_INITIAL	equ	__end_of_POWER_INITIAL-_POWER_INITIAL
	
_POWER_INITIAL:	
	opt	stack 15
; Regs used in _POWER_INITIAL: [wreg+status,2]
	line	32
	
l3643:	
;test_61f14x_TIM1_PWM.C: 32: OSCCON = 0B01110001;
	movlw	(071h)
	movlb 1	; select bank1
	movwf	(153)^080h	;volatile
	line	34
	
l3645:	
;test_61f14x_TIM1_PWM.C: 34: INTCON = 0;
	clrf	(11)	;volatile
	line	36
	
l3647:	
;test_61f14x_TIM1_PWM.C: 36: PORTA = 0B00000000;
	movlb 0	; select bank0
	clrf	(12)	;volatile
	line	37
	
l3649:	
;test_61f14x_TIM1_PWM.C: 37: TRISA = 0B00000000;
	movlb 1	; select bank1
	clrf	(140)^080h	;volatile
	line	38
	
l3651:	
;test_61f14x_TIM1_PWM.C: 38: PORTB = 0B00000000;
	movlb 0	; select bank0
	clrf	(13)	;volatile
	line	39
	
l3653:	
;test_61f14x_TIM1_PWM.C: 39: TRISB = 0B00000000;
	movlb 1	; select bank1
	clrf	(141)^080h	;volatile
	line	40
	
l3655:	
;test_61f14x_TIM1_PWM.C: 40: PORTC = 0B00000000;
	movlb 0	; select bank0
	clrf	(14)	;volatile
	line	41
	
l3657:	
;test_61f14x_TIM1_PWM.C: 41: TRISC = 0B00000000;
	movlb 1	; select bank1
	clrf	(142)^080h	;volatile
	line	43
	
l3659:	
;test_61f14x_TIM1_PWM.C: 43: WPUA = 0B00000000;
	movlb 3	; select bank3
	clrf	(396)^0180h	;volatile
	line	44
	
l3661:	
;test_61f14x_TIM1_PWM.C: 44: WPUB = 0B00000000;
	clrf	(397)^0180h	;volatile
	line	45
	
l3663:	
;test_61f14x_TIM1_PWM.C: 45: WPUC = 0B00000000;
	clrf	(398)^0180h	;volatile
	line	47
	
l3665:	
;test_61f14x_TIM1_PWM.C: 47: WPDA = 0B00000000;
	movlb 4	; select bank4
	clrf	(524)^0200h	;volatile
	line	48
	
l3667:	
;test_61f14x_TIM1_PWM.C: 48: WPDB = 0B00000000;
	clrf	(525)^0200h	;volatile
	line	49
	
l3669:	
;test_61f14x_TIM1_PWM.C: 49: WPDC = 0B00000000;
	clrf	(526)^0200h	;volatile
	line	51
	
l3671:	
;test_61f14x_TIM1_PWM.C: 51: PSRC0 = 0B11111111;
	movlw	(0FFh)
	movlb 2	; select bank2
	movwf	(282)^0100h	;volatile
	line	52
	
l3673:	
;test_61f14x_TIM1_PWM.C: 52: PSRC1 = 0B11111111;
	movlw	(0FFh)
	movwf	(283)^0100h	;volatile
	line	54
	
l3675:	
;test_61f14x_TIM1_PWM.C: 54: PSINK0 = 0B11111111;
	movlw	(0FFh)
	movlb 3	; select bank3
	movwf	(410)^0180h	;volatile
	line	55
	
l3677:	
;test_61f14x_TIM1_PWM.C: 55: PSINK1 = 0B11111111;
	movlw	(0FFh)
	movwf	(411)^0180h	;volatile
	line	56
	
l3679:	
;test_61f14x_TIM1_PWM.C: 56: PSINK2 = 0B11111111;
	movlw	(0FFh)
	movwf	(412)^0180h	;volatile
	line	58
;test_61f14x_TIM1_PWM.C: 58: ANSELA = 0B00000000;
	clrf	(407)^0180h	;volatile
	line	59
	
l1595:	
	return
	opt stack 0
GLOBAL	__end_of_POWER_INITIAL
	__end_of_POWER_INITIAL:
;; =============== function _POWER_INITIAL ends ============

	signat	_POWER_INITIAL,88
psect	text40,local,class=CODE,delta=2
global __ptext40
__ptext40:
	global	btemp
	btemp set 07Eh

	DABS	1,126,2	;btemp
	global	wtemp0
	wtemp0 set btemp
	end
