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
	FNCALL	_main,_UART_INITIAL
	FNCALL	_main,_DelayMs
	FNCALL	_DelayMs,_DelayUs
	FNROOT	_main
	FNCALL	intlevel1,_ISR
	global	intlevel1
	FNROOT	intlevel1
	global	_toSend
psect	idataBANK0,class=CODE,space=0,delta=2
global __pidataBANK0
__pidataBANK0:
	file	"test_61f14x_USART.C"
	line	30

;initializer for _toSend
	retlw	011h
	retlw	022h
	retlw	033h
	retlw	044h
	retlw	055h
	retlw	066h
	retlw	077h
	retlw	088h
	retlw	099h
	retlw	0AAh
	retlw	0
	global	_receivedata
	global	_i
	global	_mmm
	global	_receive_flag
	global	_senddata
	global	_INTCON
_INTCON	set	11
	global	_PORTA
_PORTA	set	12
	global	_PORTB
_PORTB	set	13
	global	_PORTC
_PORTC	set	14
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
	global	_WPDA
_WPDA	set	524
	global	_WPDB
_WPDB	set	525
	global	_WPDC
_WPDC	set	526
	global	_URDATAL
_URDATAL	set	1164
	global	_URDLH
_URDLH	set	1173
	global	_URDLL
_URDLL	set	1172
	global	_URIER
_URIER	set	1166
	global	_URLCR
_URLCR	set	1167
	global	_URMCR
_URMCR	set	1169
	global	_RXNEF
_RXNEF	set	9360
	global	_TCEN
_TCEN	set	9333
	global	_TCF
_TCF	set	9440
	global	_TXEF
_TXEF	set	9365
	global	_URRXNE
_URRXNE	set	9328
	file	"test_61f14x_usart.as"
	line	#
psect cinit,class=CODE,delta=2
global start_initialization
start_initialization:

psect	bssCOMMON,class=COMMON,space=1
global __pbssCOMMON
__pbssCOMMON:
_i:
       ds      1

_mmm:
       ds      1

_receive_flag:
       ds      1

_senddata:
       ds      1

psect	bssBANK0,class=BANK0,space=1
global __pbssBANK0
__pbssBANK0:
_receivedata:
       ds      10

psect	dataBANK0,class=BANK0,space=1
global __pdataBANK0
__pdataBANK0:
	file	"test_61f14x_USART.C"
_toSend:
       ds      11

; Clear objects allocated to COMMON
psect cinit,class=CODE,delta=2
	global __pbssCOMMON
	clrf	((__pbssCOMMON)+0)&07Fh
	clrf	((__pbssCOMMON)+1)&07Fh
	clrf	((__pbssCOMMON)+2)&07Fh
	clrf	((__pbssCOMMON)+3)&07Fh
; Clear objects allocated to BANK0
psect cinit,class=CODE,delta=2
	global __pbssBANK0
	clrf	((__pbssBANK0)+0)&07Fh
	clrf	((__pbssBANK0)+1)&07Fh
	clrf	((__pbssBANK0)+2)&07Fh
	clrf	((__pbssBANK0)+3)&07Fh
	clrf	((__pbssBANK0)+4)&07Fh
	clrf	((__pbssBANK0)+5)&07Fh
	clrf	((__pbssBANK0)+6)&07Fh
	clrf	((__pbssBANK0)+7)&07Fh
	clrf	((__pbssBANK0)+8)&07Fh
	clrf	((__pbssBANK0)+9)&07Fh
; Initialize objects allocated to BANK0
	global __pidataBANK0,__pdataBANK0
psect cinit,class=CODE,delta=2
	fcall	__pidataBANK0+0		;fetch initializer
	movwf	__pdataBANK0+0&07fh		
	fcall	__pidataBANK0+1		;fetch initializer
	movwf	__pdataBANK0+1&07fh		
	fcall	__pidataBANK0+2		;fetch initializer
	movwf	__pdataBANK0+2&07fh		
	fcall	__pidataBANK0+3		;fetch initializer
	movwf	__pdataBANK0+3&07fh		
	fcall	__pidataBANK0+4		;fetch initializer
	movwf	__pdataBANK0+4&07fh		
	fcall	__pidataBANK0+5		;fetch initializer
	movwf	__pdataBANK0+5&07fh		
	fcall	__pidataBANK0+6		;fetch initializer
	movwf	__pdataBANK0+6&07fh		
	fcall	__pidataBANK0+7		;fetch initializer
	movwf	__pdataBANK0+7&07fh		
	fcall	__pidataBANK0+8		;fetch initializer
	movwf	__pdataBANK0+8&07fh		
	fcall	__pidataBANK0+9		;fetch initializer
	movwf	__pdataBANK0+9&07fh		
	fcall	__pidataBANK0+10		;fetch initializer
	movwf	__pdataBANK0+10&07fh		
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
	global	?_DelayUs
?_DelayUs:	; 0 bytes @ 0x0
	global	??_DelayUs
??_DelayUs:	; 0 bytes @ 0x0
	global	?_DelayMs
?_DelayMs:	; 0 bytes @ 0x0
	global	?_UART_INITIAL
?_UART_INITIAL:	; 0 bytes @ 0x0
	global	??_UART_INITIAL
??_UART_INITIAL:	; 0 bytes @ 0x0
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
;;Data sizes: Strings 0, constant 0, data 11, bss 14, persistent 0 stack 0
;;Auto spaces:   Size  Autos    Used
;; COMMON          14      5       9
;; BANK0           80      0      21
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
;; (0) _main                                                 0     0      0      90
;;                      _POWER_INITIAL
;;                       _UART_INITIAL
;;                            _DelayMs
;; ---------------------------------------------------------------------------------
;; (1) _DelayMs                                              3     3      0      90
;;                                              2 COMMON     3     3      0
;;                            _DelayUs
;; ---------------------------------------------------------------------------------
;; (2) _DelayUs                                              2     2      0      30
;;                                              0 COMMON     2     2      0
;; ---------------------------------------------------------------------------------
;; (1) _UART_INITIAL                                         0     0      0       0
;; ---------------------------------------------------------------------------------
;; (1) _POWER_INITIAL                                        0     0      0       0
;; ---------------------------------------------------------------------------------
;; Estimated maximum stack depth 2
;; ---------------------------------------------------------------------------------
;; (Depth) Function   	        Calls       Base Space   Used Autos Params    Refs
;; ---------------------------------------------------------------------------------
;; (3) _ISR                                                  0     0      0       0
;; ---------------------------------------------------------------------------------
;; Estimated maximum stack depth 3
;; ---------------------------------------------------------------------------------

;; Call Graph Graphs:

;; _main (ROOT)
;;   _POWER_INITIAL
;;   _UART_INITIAL
;;   _DelayMs
;;     _DelayUs
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
;;COMMON               E      5       9       2       64.3%
;;BITSFR1              0      0       0       2        0.0%
;;SFR1                 0      0       0       2        0.0%
;;BITSFR2              0      0       0       3        0.0%
;;SFR2                 0      0       0       3        0.0%
;;STACK                0      0       2       3        0.0%
;;BITSFR3              0      0       0       4        0.0%
;;SFR3                 0      0       0       4        0.0%
;;ABS                  0      0      1E       4        0.0%
;;BITBANK0            50      0       0       5        0.0%
;;BITSFR4              0      0       0       5        0.0%
;;SFR4                 0      0       0       5        0.0%
;;BANK0               50      0      15       6       26.3%
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
;;DATA                 0      0      20      19        0.0%
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
;;		line 163 in file "test_61f14x_USART.C"
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
;; Hardware stack levels required when called:    3
;; This function calls:
;;		_POWER_INITIAL
;;		_UART_INITIAL
;;		_DelayMs
;; This function is called by:
;;		Startup code after reset
;; This function uses a non-reentrant model
;;
psect	maintext
	file	"test_61f14x_USART.C"
	line	163
	global	__size_of_main
	__size_of_main	equ	__end_of_main-_main
	
_main:	
	opt	stack 13
; Regs used in _main: [wreg+status,2+status,0+pclath+cstack]
	line	164
	
l3779:	
;test_61f14x_USART.C: 164: POWER_INITIAL();
	fcall	_POWER_INITIAL
	line	165
;test_61f14x_USART.C: 165: UART_INITIAL();
	fcall	_UART_INITIAL
	line	166
;test_61f14x_USART.C: 166: DelayMs(100);
	movlw	(064h)
	fcall	_DelayMs
	line	168
	
l3781:	
;test_61f14x_USART.C: 168: if(TXEF)
	movlb 9	; select bank9
	btfss	(9365/8)^0480h,(9365)&7
	goto	u101
	goto	u100
u101:
	goto	l3785
u100:
	line	170
	
l3783:	
;test_61f14x_USART.C: 169: {
;test_61f14x_USART.C: 170: URDATAL =0xaa;
	movlw	(0AAh)
	movlb 9	; select bank9
	movwf	(1164)^0480h	;volatile
	line	175
	
l3785:	
;test_61f14x_USART.C: 174: {
;test_61f14x_USART.C: 175: _nop();
	nop
	line	176
	
l3787:	
;test_61f14x_USART.C: 176: DelayMs(250);
	movlw	(0FAh)
	fcall	_DelayMs
	line	178
	
l3789:	
;test_61f14x_USART.C: 178: if(receive_flag == 1)
	decf	(_receive_flag),w	;volatile
	skipz
	goto	u111
	goto	u110
u111:
	goto	l3785
u110:
	line	180
	
l3791:	
;test_61f14x_USART.C: 179: {
;test_61f14x_USART.C: 180: receive_flag = 0;
	clrf	(_receive_flag)	;volatile
	goto	l3783
	global	start
	ljmp	start
	opt stack 0
psect	maintext
	line	185
GLOBAL	__end_of_main
	__end_of_main:
;; =============== function _main ends ============

	signat	_main,88
	global	_DelayMs
psect	text113,local,class=CODE,delta=2
global __ptext113
__ptext113:

;; *************** function _DelayMs *****************
;; Defined at:
;;		line 123 in file "test_61f14x_USART.C"
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
;;		On entry : 0/9
;;		On exit  : 0/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         3       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         3       0       0       0       0       0       0       0
;;Total ram usage:        3 bytes
;; Hardware stack levels used:    1
;; Hardware stack levels required when called:    2
;; This function calls:
;;		_DelayUs
;; This function is called by:
;;		_main
;; This function uses a non-reentrant model
;;
psect	text113
	file	"test_61f14x_USART.C"
	line	123
	global	__size_of_DelayMs
	__size_of_DelayMs	equ	__end_of_DelayMs-_DelayMs
	
_DelayMs:	
	opt	stack 13
; Regs used in _DelayMs: [wreg+status,2+status,0+pclath+cstack]
;DelayMs@Time stored from wreg
	line	125
	movwf	(DelayMs@Time)
	
l3761:	
;test_61f14x_USART.C: 124: unsigned char a,b;
;test_61f14x_USART.C: 125: for(a=0;a<Time;a++)
	clrf	(DelayMs@a)
	goto	l3777
	line	127
	
l3763:	
;test_61f14x_USART.C: 126: {
;test_61f14x_USART.C: 127: for(b=0;b<5;b++)
	clrf	(DelayMs@b)
	line	129
	
l3769:	
;test_61f14x_USART.C: 128: {
;test_61f14x_USART.C: 129: DelayUs(197);
	movlw	(0C5h)
	fcall	_DelayUs
	line	127
	
l3771:	
	incf	(DelayMs@b),f
	
l3773:	
	movlw	(05h)
	subwf	(DelayMs@b),w
	skipc
	goto	u81
	goto	u80
u81:
	goto	l3769
u80:
	line	125
	
l3775:	
	incf	(DelayMs@a),f
	
l3777:	
	movf	(DelayMs@Time),w
	subwf	(DelayMs@a),w
	skipc
	goto	u91
	goto	u90
u91:
	goto	l3763
u90:
	line	132
	
l1629:	
	return
	opt stack 0
GLOBAL	__end_of_DelayMs
	__end_of_DelayMs:
;; =============== function _DelayMs ends ============

	signat	_DelayMs,4216
	global	_DelayUs
psect	text114,local,class=CODE,delta=2
global __ptext114
__ptext114:

;; *************** function _DelayUs *****************
;; Defined at:
;;		line 109 in file "test_61f14x_USART.C"
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
;;		On entry : 0/9
;;		On exit  : 0/0
;;		Unchanged: 0/0
;; Data sizes:     COMMON   BANK0   BANK1   BANK2   BANK3   BANK4   BANK5   BANK6
;;      Params:         0       0       0       0       0       0       0       0
;;      Locals:         2       0       0       0       0       0       0       0
;;      Temps:          0       0       0       0       0       0       0       0
;;      Totals:         2       0       0       0       0       0       0       0
;;Total ram usage:        2 bytes
;; Hardware stack levels used:    1
;; Hardware stack levels required when called:    1
;; This function calls:
;;		Nothing
;; This function is called by:
;;		_DelayMs
;; This function uses a non-reentrant model
;;
psect	text114
	file	"test_61f14x_USART.C"
	line	109
	global	__size_of_DelayUs
	__size_of_DelayUs	equ	__end_of_DelayUs-_DelayUs
	
_DelayUs:	
	opt	stack 13
; Regs used in _DelayUs: [wreg+status,2+status,0]
;DelayUs@Time stored from wreg
	line	111
	movwf	(DelayUs@Time)
	
l3755:	
;test_61f14x_USART.C: 110: unsigned char a;
;test_61f14x_USART.C: 111: for(a=0;a<Time;a++)
	clrf	(DelayUs@a)
	goto	l3759
	line	112
	
l1619:	
	line	113
;test_61f14x_USART.C: 112: {
;test_61f14x_USART.C: 113: _nop();
	nop
	line	111
	
l3757:	
	incf	(DelayUs@a),f
	
l3759:	
	movf	(DelayUs@Time),w
	subwf	(DelayUs@a),w
	skipc
	goto	u71
	goto	u70
u71:
	goto	l1619
u70:
	line	115
	
l1621:	
	return
	opt stack 0
GLOBAL	__end_of_DelayUs
	__end_of_DelayUs:
;; =============== function _DelayUs ends ============

	signat	_DelayUs,4216
	global	_UART_INITIAL
psect	text115,local,class=CODE,delta=2
global __ptext115
__ptext115:

;; *************** function _UART_INITIAL *****************
;; Defined at:
;;		line 140 in file "test_61f14x_USART.C"
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
;;		On exit  : 17F/9
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
psect	text115
	file	"test_61f14x_USART.C"
	line	140
	global	__size_of_UART_INITIAL
	__size_of_UART_INITIAL	equ	__end_of_UART_INITIAL-_UART_INITIAL
	
_UART_INITIAL:	
	opt	stack 14
; Regs used in _UART_INITIAL: [wreg+status,2]
	line	141
	
l3745:	
;test_61f14x_USART.C: 141: PCKEN |=0B00100000;
	movlb 1	; select bank1
	bsf	(154)^080h+(5/8),(5)&7	;volatile
	line	143
	
l3747:	
;test_61f14x_USART.C: 143: URIER =0B00100001;
	movlw	(021h)
	movlb 9	; select bank9
	movwf	(1166)^0480h	;volatile
	line	144
;test_61f14x_USART.C: 144: URLCR =0B00000001;
	movlw	(01h)
	movwf	(1167)^0480h	;volatile
	line	145
;test_61f14x_USART.C: 145: URMCR =0B00011000;
	movlw	(018h)
	movwf	(1169)^0480h	;volatile
	line	147
;test_61f14x_USART.C: 147: URDLL =104;
	movlw	(068h)
	movwf	(1172)^0480h	;volatile
	line	148
	
l3749:	
;test_61f14x_USART.C: 148: URDLH =0;
	clrf	(1173)^0480h	;volatile
	line	149
	
l3751:	
;test_61f14x_USART.C: 149: TCF=1;
	bsf	(9440/8)^0480h,(9440)&7
	line	150
	
l3753:	
;test_61f14x_USART.C: 150: INTCON=0B11000000;
	movlw	(0C0h)
	movwf	(11)	;volatile
	line	155
	
l1632:	
	return
	opt stack 0
GLOBAL	__end_of_UART_INITIAL
	__end_of_UART_INITIAL:
;; =============== function _UART_INITIAL ends ============

	signat	_UART_INITIAL,88
	global	_POWER_INITIAL
psect	text116,local,class=CODE,delta=2
global __ptext116
__ptext116:

;; *************** function _POWER_INITIAL *****************
;; Defined at:
;;		line 74 in file "test_61f14x_USART.C"
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
psect	text116
	file	"test_61f14x_USART.C"
	line	74
	global	__size_of_POWER_INITIAL
	__size_of_POWER_INITIAL	equ	__end_of_POWER_INITIAL-_POWER_INITIAL
	
_POWER_INITIAL:	
	opt	stack 14
; Regs used in _POWER_INITIAL: [wreg+status,2]
	line	75
	
l3711:	
;test_61f14x_USART.C: 75: OSCCON = 0B01110001;
	movlw	(071h)
	movlb 1	; select bank1
	movwf	(153)^080h	;volatile
	line	76
	
l3713:	
;test_61f14x_USART.C: 76: INTCON = 0;
	clrf	(11)	;volatile
	line	78
	
l3715:	
;test_61f14x_USART.C: 78: PORTA = 0B00000000;
	movlb 0	; select bank0
	clrf	(12)	;volatile
	line	79
;test_61f14x_USART.C: 79: TRISA = 0B10000000;
	movlw	(080h)
	movlb 1	; select bank1
	movwf	(140)^080h	;volatile
	line	80
	
l3717:	
;test_61f14x_USART.C: 80: PORTB = 0B00000000;
	movlb 0	; select bank0
	clrf	(13)	;volatile
	line	81
	
l3719:	
;test_61f14x_USART.C: 81: TRISB = 0B00000000;
	movlb 1	; select bank1
	clrf	(141)^080h	;volatile
	line	82
	
l3721:	
;test_61f14x_USART.C: 82: PORTC = 0B00000000;
	movlb 0	; select bank0
	clrf	(14)	;volatile
	line	83
	
l3723:	
;test_61f14x_USART.C: 83: TRISC = 0B00000000;
	movlb 1	; select bank1
	clrf	(142)^080h	;volatile
	line	85
	
l3725:	
;test_61f14x_USART.C: 85: WPUA = 0B00000000;
	movlb 3	; select bank3
	clrf	(396)^0180h	;volatile
	line	86
	
l3727:	
;test_61f14x_USART.C: 86: WPUB = 0B00000000;
	clrf	(397)^0180h	;volatile
	line	87
	
l3729:	
;test_61f14x_USART.C: 87: WPUC = 0B00000000;
	clrf	(398)^0180h	;volatile
	line	89
	
l3731:	
;test_61f14x_USART.C: 89: WPDA = 0B10000000;
	movlw	(080h)
	movlb 4	; select bank4
	movwf	(524)^0200h	;volatile
	line	90
;test_61f14x_USART.C: 90: WPDB = 0B00000000;
	clrf	(525)^0200h	;volatile
	line	91
;test_61f14x_USART.C: 91: WPDC = 0B00000000;
	clrf	(526)^0200h	;volatile
	line	93
	
l3733:	
;test_61f14x_USART.C: 93: PSRC0 = 0B11111111;
	movlw	(0FFh)
	movlb 2	; select bank2
	movwf	(282)^0100h	;volatile
	line	94
	
l3735:	
;test_61f14x_USART.C: 94: PSRC1 = 0B11111111;
	movlw	(0FFh)
	movwf	(283)^0100h	;volatile
	line	96
	
l3737:	
;test_61f14x_USART.C: 96: PSINK0 = 0B11111111;
	movlw	(0FFh)
	movlb 3	; select bank3
	movwf	(410)^0180h	;volatile
	line	97
	
l3739:	
;test_61f14x_USART.C: 97: PSINK1 = 0B11111111;
	movlw	(0FFh)
	movwf	(411)^0180h	;volatile
	line	98
	
l3741:	
;test_61f14x_USART.C: 98: PSINK2 = 0B11111111;
	movlw	(0FFh)
	movwf	(412)^0180h	;volatile
	line	100
	
l3743:	
;test_61f14x_USART.C: 100: ANSELA = 0B00000000;
	clrf	(407)^0180h	;volatile
	line	101
	
l1615:	
	return
	opt stack 0
GLOBAL	__end_of_POWER_INITIAL
	__end_of_POWER_INITIAL:
;; =============== function _POWER_INITIAL ends ============

	signat	_POWER_INITIAL,88
	global	_ISR
psect	intentry,class=CODE,delta=2
global __pintentry
__pintentry:

;; *************** function _ISR *****************
;; Defined at:
;;		line 40 in file "test_61f14x_USART.C"
;; Parameters:    Size  Location     Type
;;		None
;; Auto vars:     Size  Location     Type
;;		None
;; Return value:  Size  Location     Type
;;		None               void
;; Registers used:
;;		wreg, fsr1l, fsr1h, status,2, status,0
;; Tracked objects:
;;		On entry : 0/0
;;		On exit  : 0/0
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
	file	"test_61f14x_USART.C"
	line	40
	global	__size_of_ISR
	__size_of_ISR	equ	__end_of_ISR-_ISR
	
_ISR:	
	opt	stack 13
; Regs used in _ISR: [wreg+fsr1l-status,0]
psect	intentry
	pagesel	$
	line	41
	
i1l3795:	
;test_61f14x_USART.C: 41: if(URRXNE && RXNEF)
	movlb 9	; select bank9
	btfss	(9328/8)^0480h,(9328)&7
	goto	u12_21
	goto	u12_20
u12_21:
	goto	i1l3811
u12_20:
	
i1l3797:	
	btfss	(9360/8)^0480h,(9360)&7
	goto	u13_21
	goto	u13_20
u13_21:
	goto	i1l3811
u13_20:
	line	43
	
i1l3799:	
;test_61f14x_USART.C: 42: {
;test_61f14x_USART.C: 43: receivedata[mmm++] =URDATAL;
	movf	(_mmm),w
	addlw	_receivedata&0ffh
	movwf	fsr1l
	clrf fsr1h	
	
	movf	(1164)^0480h,w	;volatile
	movwf	indf1
	
i1l3801:	
	incf	(_mmm),f
	line	44
	
i1l3803:	
;test_61f14x_USART.C: 44: receive_flag = 1;
	clrf	(_receive_flag)	;volatile
	incf	(_receive_flag),f	;volatile
	line	45
	
i1l3805:	
;test_61f14x_USART.C: 45: if(mmm>=10)
	movlw	(0Ah)
	subwf	(_mmm),w
	skipc
	goto	u14_21
	goto	u14_20
u14_21:
	goto	i1l3809
u14_20:
	line	47
	
i1l3807:	
;test_61f14x_USART.C: 46: {
;test_61f14x_USART.C: 47: mmm=0;
	clrf	(_mmm)
	line	49
	
i1l3809:	
;test_61f14x_USART.C: 48: }
;test_61f14x_USART.C: 49: _nop();
	nop
	line	52
	
i1l3811:	
;test_61f14x_USART.C: 50: }
;test_61f14x_USART.C: 52: if(TCEN && TCF)
	movlb 9	; select bank9
	btfss	(9333/8)^0480h,(9333)&7
	goto	u15_21
	goto	u15_20
u15_21:
	goto	i1l1612
u15_20:
	
i1l3813:	
	btfss	(9440/8)^0480h,(9440)&7
	goto	u16_21
	goto	u16_20
u16_21:
	goto	i1l1612
u16_20:
	line	54
	
i1l3815:	
;test_61f14x_USART.C: 53: {
;test_61f14x_USART.C: 54: TCF=1;
	bsf	(9440/8)^0480h,(9440)&7
	line	56
	
i1l3817:	
;test_61f14x_USART.C: 56: if(i<10)
	movlw	(0Ah)
	subwf	(_i),w
	skipnc
	goto	u17_21
	goto	u17_20
u17_21:
	goto	i1l3823
u17_20:
	line	58
	
i1l3819:	
;test_61f14x_USART.C: 57: {
;test_61f14x_USART.C: 58: URDATAL =toSend[i++];
	movf	(_i),w
	addlw	_toSend&0ffh
	movwf	fsr1l
	clrf fsr1h	
	
	movf	indf1,w
	movwf	(1164)^0480h	;volatile
	
i1l3821:	
	incf	(_i),f
	line	59
;test_61f14x_USART.C: 59: }
	goto	i1l3825
	line	62
	
i1l3823:	
;test_61f14x_USART.C: 60: else
;test_61f14x_USART.C: 61: {
;test_61f14x_USART.C: 62: i=0;
	clrf	(_i)
	line	64
	
i1l3825:	
;test_61f14x_USART.C: 63: }
;test_61f14x_USART.C: 64: _nop();
	nop
	line	66
	
i1l1612:	
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
