//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_IRSendStatus		EQU		79H
		_IRSendData		EQU		78H
		_TxBit		EQU		77H
		_TxTime		EQU		76H
		_SendBit		EQU		75H
		_level0		EQU		74H
		_level1		EQU		73H
		_SendLastBit		EQU		7DH
		_SaveLastBit		EQU		72H
		_SYSTime5S		EQU		70H
		_IRData		EQU		20H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	1BH 			//0001 	381B
		ORG		0004H
		BSR 	7EH, 0H 			//0004 	247E
		MOVLP 	0H 			//0005 	0180

		//;test_61f14x_IR_Send.C: 399: if(T4UIE && T4UIF)
		MOVLB 	2H 			//0006 	1022
		BTSC 	12H, 0H 		//0007 	2812
		BTSS 	13H, 0H 		//0008 	2C13
		LJUMP 	11H 			//0009 	3811

		//;test_61f14x_IR_Send.C: 400: {
		//;test_61f14x_IR_Send.C: 401: T4UIF = 1;
		BSR 	13H, 0H 			//000A 	2413

		//;test_61f14x_IR_Send.C: 403: SendCtrl();
		MOVLP 	0H 			//000B 	0180
		ORG		000CH
		LCALL 	87H 			//000C 	3087
		MOVLP 	0H 			//000D 	0180

		//;test_61f14x_IR_Send.C: 404: SYSTime5S++;
		INCR 	70H, 1H 		//000E 	1AF0
		BTSC 	3H, 2H 			//000F 	2903
		INCR 	71H, 1H 		//0010 	1AF1

		//;test_61f14x_IR_Send.C: 405: }
		//;test_61f14x_IR_Send.C: 407: if(T2UIE && T2UIF)
		MOVLB 	6H 			//0011 	1026
		BTSC 	DH, 0H 			//0012 	280D
		BTSS 	EH, 0H 			//0013 	2C0E
		ORG		0014H
		LJUMP 	19H 			//0014 	3819

		//;test_61f14x_IR_Send.C: 408: {
		//;test_61f14x_IR_Send.C: 409: T2UIF = 1;
		BSR 	EH, 0H 			//0015 	240E

		//;test_61f14x_IR_Send.C: 410: PB3 = ~PB3;
		LDWI 	8H 			//0016 	0008
		MOVLB 	0H 			//0017 	1020
		XORWR 	DH, 1H 		//0018 	168D
		BCR 	7EH, 0H 			//0019 	207E
		RETI 					//001A 	1009
		MOVLP 	0H 			//001B 	0180
		ORG		001CH
		LJUMP 	1DH 			//001C 	381D
		LDWI 	FFH 			//001D 	00FF
		CLRF 	20H 			//001E 	11A0
		STR 	21H 			//001F 	10A1
		LDWI 	40H 			//0020 	0040
		STR 	22H 			//0021 	10A2
		LDWI 	BFH 			//0022 	00BF
		STR 	23H 			//0023 	10A3
		ORG		0024H
		CLRF 	7DH 			//0024 	11FD
		CLRF 	70H 			//0025 	11F0
		CLRF 	71H 			//0026 	11F1
		CLRF 	72H 			//0027 	11F2
		CLRF 	73H 			//0028 	11F3
		CLRF 	74H 			//0029 	11F4
		CLRF 	75H 			//002A 	11F5
		CLRF 	76H 			//002B 	11F6
		ORG		002CH
		CLRF 	77H 			//002C 	11F7
		CLRF 	78H 			//002D 	11F8
		CLRF 	79H 			//002E 	11F9
		BCR 	7EH, 0H 			//002F 	207E
		MOVLB 	0H 			//0030 	1020
		LJUMP 	32H 			//0031 	3832

		//;test_61f14x_IR_Send.C: 421: POWER_INITIAL();
		LCALL 	45H 			//0032 	3045
		MOVLP 	0H 			//0033 	0180
		ORG		0034H

		//;test_61f14x_IR_Send.C: 422: TIMER4_INITIAL();
		LCALL 	7AH 			//0034 	307A
		MOVLP 	0H 			//0035 	0180

		//;test_61f14x_IR_Send.C: 423: TIMER2_INITIAL();
		LCALL 	6AH 			//0036 	306A
		MOVLP 	0H 			//0037 	0180

		//;test_61f14x_IR_Send.C: 424: GIE = 1;
		BSR 	BH, 7H 			//0038 	278B

		//;test_61f14x_IR_Send.C: 426: {
		//;test_61f14x_IR_Send.C: 427: if(SYSTime5S >5000)
		LDWI 	13H 			//0039 	0013
		SUBWR 	71H, 0H 		//003A 	1271
		LDWI 	89H 			//003B 	0089
		ORG		003CH
		BTSC 	3H, 2H 			//003C 	2903
		SUBWR 	70H, 0H 		//003D 	1270
		BTSS 	3H, 0H 			//003E 	2C03
		LJUMP 	39H 			//003F 	3839

		//;test_61f14x_IR_Send.C: 428: {
		//;test_61f14x_IR_Send.C: 429: SYSTime5S = 0;
		CLRF 	70H 			//0040 	11F0
		CLRF 	71H 			//0041 	11F1

		//;test_61f14x_IR_Send.C: 430: IRSendStatus = 1;
		CLRF 	79H 			//0042 	11F9
		INCR 	79H, 1H 		//0043 	1AF9
		ORG		0044H
		LJUMP 	39H 			//0044 	3839

		//;test_61f14x_IR_Send.C: 62: OSCCON = 0B01110001;
		LDWI 	71H 			//0045 	0071
		MOVLB 	1H 			//0046 	1021
		STR 	19H 			//0047 	1099

		//;test_61f14x_IR_Send.C: 63: PCKEN |=0B00001100;
		LDWI 	CH 			//0048 	000C
		IORWR 	1AH, 1H 		//0049 	149A

		//;test_61f14x_IR_Send.C: 66: INTCON = 0;
		CLRF 	BH 			//004A 	118B

		//;test_61f14x_IR_Send.C: 68: PORTA = 0B00000000;
		MOVLB 	0H 			//004B 	1020
		ORG		004CH
		CLRF 	CH 			//004C 	118C

		//;test_61f14x_IR_Send.C: 69: TRISA = 0B00000000;
		MOVLB 	1H 			//004D 	1021
		CLRF 	CH 			//004E 	118C

		//;test_61f14x_IR_Send.C: 70: PORTB = 0B00000000;
		MOVLB 	0H 			//004F 	1020
		CLRF 	DH 			//0050 	118D

		//;test_61f14x_IR_Send.C: 71: TRISB = 0B00000000;
		MOVLB 	1H 			//0051 	1021
		CLRF 	DH 			//0052 	118D

		//;test_61f14x_IR_Send.C: 72: PORTC = 0B00000000;
		MOVLB 	0H 			//0053 	1020
		ORG		0054H
		CLRF 	EH 			//0054 	118E

		//;test_61f14x_IR_Send.C: 73: TRISC = 0B00000000;
		MOVLB 	1H 			//0055 	1021
		CLRF 	EH 			//0056 	118E

		//;test_61f14x_IR_Send.C: 75: WPUA = 0B00000000;
		MOVLB 	3H 			//0057 	1023
		CLRF 	CH 			//0058 	118C

		//;test_61f14x_IR_Send.C: 76: WPUB = 0B00000000;
		CLRF 	DH 			//0059 	118D

		//;test_61f14x_IR_Send.C: 77: WPUC = 0B00000001;
		LDWI 	1H 			//005A 	0001
		STR 	EH 			//005B 	108E
		ORG		005CH

		//;test_61f14x_IR_Send.C: 79: WPDA = 0B00000000;
		MOVLB 	4H 			//005C 	1024
		CLRF 	CH 			//005D 	118C

		//;test_61f14x_IR_Send.C: 80: WPDB = 0B00000000;
		CLRF 	DH 			//005E 	118D

		//;test_61f14x_IR_Send.C: 81: WPDC = 0B00000000;
		CLRF 	EH 			//005F 	118E

		//;test_61f14x_IR_Send.C: 83: PSRC0 = 0B11111111;
		LDWI 	FFH 			//0060 	00FF
		MOVLB 	2H 			//0061 	1022
		STR 	1AH 			//0062 	109A

		//;test_61f14x_IR_Send.C: 84: PSRC1 = 0B11111111;
		STR 	1BH 			//0063 	109B
		ORG		0064H

		//;test_61f14x_IR_Send.C: 86: PSINK0 = 0B11111111;
		MOVLB 	3H 			//0064 	1023
		STR 	1AH 			//0065 	109A

		//;test_61f14x_IR_Send.C: 87: PSINK1 = 0B11111111;
		STR 	1BH 			//0066 	109B

		//;test_61f14x_IR_Send.C: 88: PSINK2 = 0B11111111;
		STR 	1CH 			//0067 	109C

		//;test_61f14x_IR_Send.C: 90: ANSELA = 0B00000000;
		CLRF 	17H 			//0068 	1197
		RET 					//0069 	1008

		//;test_61f14x_IR_Send.C: 165: CKOCON=0B00100000;
		LDWI 	20H 			//006A 	0020
		MOVLB 	1H 			//006B 	1021
		ORG		006CH
		STR 	15H 			//006C 	1095

		//;test_61f14x_IR_Send.C: 166: TCKSRC=0B00110000;
		LDWI 	30H 			//006D 	0030
		MOVLB 	6H 			//006E 	1026
		STR 	1FH 			//006F 	109F

		//;test_61f14x_IR_Send.C: 191: TIM2CR1 =0B10000101;
		LDWI 	85H 			//0070 	0085
		STR 	CH 			//0071 	108C

		//;test_61f14x_IR_Send.C: 229: TIM2IER =0B00000000;
		CLRF 	DH 			//0072 	118D

		//;test_61f14x_IR_Send.C: 262: TIM2ARRH = 0x01;
		LDWI 	1H 			//0073 	0001
		ORG		0074H
		STR 	19H 			//0074 	1099

		//;test_61f14x_IR_Send.C: 263: TIM2ARRL = 0xA0;
		LDWI 	A0H 			//0075 	00A0
		STR 	1AH 			//0076 	109A

		//;test_61f14x_IR_Send.C: 265: INTCON = 0B11000000;
		LDWI 	C0H 			//0077 	00C0
		STR 	BH 			//0078 	108B
		RET 					//0079 	1008

		//;test_61f14x_IR_Send.C: 100: TIM4CR1 =0B00000101;
		LDWI 	5H 			//007A 	0005
		MOVLB 	2H 			//007B 	1022
		ORG		007CH
		STR 	11H 			//007C 	1091

		//;test_61f14x_IR_Send.C: 130: TIM4IER =0B00000001;
		LDWI 	1H 			//007D 	0001
		STR 	12H 			//007E 	1092

		//;test_61f14x_IR_Send.C: 133: TIM4SR =0B00000000;
		CLRF 	13H 			//007F 	1193

		//;test_61f14x_IR_Send.C: 142: TIM4EGR =0B00000000;
		CLRF 	14H 			//0080 	1194

		//;test_61f14x_IR_Send.C: 147: TIM4CNTR=0;
		CLRF 	15H 			//0081 	1195

		//;test_61f14x_IR_Send.C: 149: TIM4PSCR=0B00000110;
		LDWI 	6H 			//0082 	0006
		STR 	16H 			//0083 	1096
		ORG		0084H

		//;test_61f14x_IR_Send.C: 154: TIM4ARR =140;
		LDWI 	8CH 			//0084 	008C
		STR 	17H 			//0085 	1097
		RET 					//0086 	1008

		//;test_61f14x_IR_Send.C: 276: if (IRSendStatus == 0)
		LDR 	79H, 0H 			//0087 	1879
		BTSS 	3H, 2H 			//0088 	2D03
		LJUMP 	8FH 			//0089 	388F

		//;test_61f14x_IR_Send.C: 277: {
		//;test_61f14x_IR_Send.C: 278: T2UIE = 0;
		MOVLB 	6H 			//008A 	1026
		BCR 	DH, 0H 			//008B 	200D
		ORG		008CH

		//;test_61f14x_IR_Send.C: 279: SendBit = 0;
		CLRF 	75H 			//008C 	11F5

		//;test_61f14x_IR_Send.C: 280: TxTime = 0;
		CLRF 	76H 			//008D 	11F6

		//;test_61f14x_IR_Send.C: 282: }
		RET 					//008E 	1008

		//;test_61f14x_IR_Send.C: 283: else if (IRSendStatus == 1)
		DECRSZ 	79H, 0H 		//008F 	1B79
		LJUMP 	A9H 			//0090 	38A9
		LDWI 	11H 			//0091 	0011

		//;test_61f14x_IR_Send.C: 284: {
		//;test_61f14x_IR_Send.C: 285: TxTime++;
		INCR 	76H, 1H 		//0092 	1AF6

		//;test_61f14x_IR_Send.C: 286: if (TxTime < 17)
		SUBWR 	76H, 0H 		//0093 	1276
		ORG		0094H
		BTSC 	3H, 0H 			//0094 	2803
		LJUMP 	99H 			//0095 	3899

		//;test_61f14x_IR_Send.C: 287: {
		//;test_61f14x_IR_Send.C: 288: T2UIE = 1;
		MOVLB 	6H 			//0096 	1026
		BSR 	DH, 0H 			//0097 	240D

		//;test_61f14x_IR_Send.C: 289: }
		LJUMP 	A3H 			//0098 	38A3

		//;test_61f14x_IR_Send.C: 290: else if (TxTime < 24)
		LDWI 	18H 			//0099 	0018
		SUBWR 	76H, 0H 		//009A 	1276
		BTSC 	3H, 0H 			//009B 	2803
		ORG		009CH
		LJUMP 	A0H 			//009C 	38A0

		//;test_61f14x_IR_Send.C: 291: {
		//;test_61f14x_IR_Send.C: 292: T2UIE = 0;
		MOVLB 	6H 			//009D 	1026
		BCR 	DH, 0H 			//009E 	200D

		//;test_61f14x_IR_Send.C: 293: }
		LJUMP 	A3H 			//009F 	38A3
		LDWI 	2H 			//00A0 	0002

		//;test_61f14x_IR_Send.C: 294: else
		//;test_61f14x_IR_Send.C: 295: {
		//;test_61f14x_IR_Send.C: 296: TxTime = 0;
		CLRF 	76H 			//00A1 	11F6

		//;test_61f14x_IR_Send.C: 297: IRSendStatus = 2;
		STR 	79H 			//00A2 	10F9

		//;test_61f14x_IR_Send.C: 298: }
		//;test_61f14x_IR_Send.C: 299: IRSendData = IRData[0];
		MOVLB 	0H 			//00A3 	1020
		ORG		00A4H
		LDR 	20H, 0H 			//00A4 	1820
		STR 	78H 			//00A5 	10F8

		//;test_61f14x_IR_Send.C: 300: TxBit = 0x01;
		CLRF 	77H 			//00A6 	11F7
		INCR 	77H, 1H 		//00A7 	1AF7

		//;test_61f14x_IR_Send.C: 301: }
		RET 					//00A8 	1008

		//;test_61f14x_IR_Send.C: 302: else if(IRSendStatus == 2)
		LDWI 	2H 			//00A9 	0002
		XORWR 	79H, 0H 		//00AA 	1679
		BTSS 	3H, 2H 			//00AB 	2D03
		ORG		00ACH
		RET 					//00AC 	1008

		//;test_61f14x_IR_Send.C: 303: {
		//;test_61f14x_IR_Send.C: 304: if (IRSendData & TxBit)
		LDR 	78H, 0H 			//00AD 	1878
		ANDWR 	77H, 0H 		//00AE 	1577
		BTSC 	3H, 2H 			//00AF 	2903
		LJUMP 	B6H 			//00B0 	38B6
		LDWI 	3H 			//00B1 	0003

		//;test_61f14x_IR_Send.C: 305: {
		//;test_61f14x_IR_Send.C: 306: level1 = 1;
		CLRF 	73H 			//00B2 	11F3
		INCR 	73H, 1H 		//00B3 	1AF3
		ORG		00B4H

		//;test_61f14x_IR_Send.C: 307: level0 = 3;
		STR 	74H 			//00B4 	10F4

		//;test_61f14x_IR_Send.C: 308: }
		LJUMP 	BAH 			//00B5 	38BA

		//;test_61f14x_IR_Send.C: 309: else
		//;test_61f14x_IR_Send.C: 310: {
		//;test_61f14x_IR_Send.C: 311: level1 = 1;
		CLRF 	73H 			//00B6 	11F3
		INCR 	73H, 1H 		//00B7 	1AF3

		//;test_61f14x_IR_Send.C: 312: level0 = 1;
		CLRF 	74H 			//00B8 	11F4
		INCR 	74H, 1H 		//00B9 	1AF4

		//;test_61f14x_IR_Send.C: 313: }
		//;test_61f14x_IR_Send.C: 314: TxTime++;
		INCR 	76H, 1H 		//00BA 	1AF6

		//;test_61f14x_IR_Send.C: 315: if (TxTime <= level1)
		LDR 	76H, 0H 			//00BB 	1876
		ORG		00BCH
		SUBWR 	73H, 0H 		//00BC 	1273
		BTSS 	3H, 0H 			//00BD 	2C03
		LJUMP 	C2H 			//00BE 	38C2

		//;test_61f14x_IR_Send.C: 316: {
		//;test_61f14x_IR_Send.C: 317: T2UIE = 1;
		MOVLB 	6H 			//00BF 	1026
		BSR 	DH, 0H 			//00C0 	240D

		//;test_61f14x_IR_Send.C: 318: }
		RET 					//00C1 	1008

		//;test_61f14x_IR_Send.C: 319: else if (TxTime <= (level0+level1))
		LDR 	74H, 0H 			//00C2 	1874
		ADDWR 	73H, 0H 		//00C3 	1773
		ORG		00C4H
		STR 	7AH 			//00C4 	10FA
		CLRF 	7BH 			//00C5 	11FB
		RLR 	7BH, 1H 			//00C6 	1DFB
		LDR 	7BH, 0H 			//00C7 	187B
		XORWI 	80H 			//00C8 	0A80
		STR 	7CH 			//00C9 	10FC
		LDWI 	80H 			//00CA 	0080
		SUBWR 	7CH, 0H 		//00CB 	127C
		ORG		00CCH
		BTSS 	3H, 2H 			//00CC 	2D03
		LJUMP 	D0H 			//00CD 	38D0
		LDR 	76H, 0H 			//00CE 	1876
		SUBWR 	7AH, 0H 		//00CF 	127A
		BTSS 	3H, 0H 			//00D0 	2C03
		LJUMP 	D5H 			//00D1 	38D5

		//;test_61f14x_IR_Send.C: 320: {
		//;test_61f14x_IR_Send.C: 321: T2UIE = 0;
		MOVLB 	6H 			//00D2 	1026
		BCR 	DH, 0H 			//00D3 	200D
		ORG		00D4H

		//;test_61f14x_IR_Send.C: 322: }
		RET 					//00D4 	1008

		//;test_61f14x_IR_Send.C: 323: else if (SendBit < 4)
		LDWI 	4H 			//00D5 	0004
		SUBWR 	75H, 0H 		//00D6 	1275
		BTSC 	3H, 0H 			//00D7 	2803
		LJUMP 	F3H 			//00D8 	38F3

		//;test_61f14x_IR_Send.C: 324: {
		//;test_61f14x_IR_Send.C: 325: TxTime = 1;
		CLRF 	76H 			//00D9 	11F6
		INCR 	76H, 1H 		//00DA 	1AF6

		//;test_61f14x_IR_Send.C: 326: T2UIE = 1;
		MOVLB 	6H 			//00DB 	1026
		ORG		00DCH
		BSR 	DH, 0H 			//00DC 	240D

		//;test_61f14x_IR_Send.C: 327: SaveLastBit = IRSendData & TxBit;
		LDR 	78H, 0H 			//00DD 	1878
		STR 	72H 			//00DE 	10F2
		LDR 	77H, 0H 			//00DF 	1877
		ANDWR 	72H, 1H 		//00E0 	15F2

		//;test_61f14x_IR_Send.C: 328: TxBit <<= 1;
		LSLF 	77H, 1H 		//00E1 	05F7

		//;test_61f14x_IR_Send.C: 329: if (TxBit == 0x00)
		LDR 	77H, 0H 			//00E2 	1877
		BTSS 	3H, 2H 			//00E3 	2D03
		ORG		00E4H
		RET 					//00E4 	1008

		//;test_61f14x_IR_Send.C: 330: {
		//;test_61f14x_IR_Send.C: 331: TxBit = 0x01;
		CLRF 	77H 			//00E5 	11F7
		INCR 	77H, 1H 		//00E6 	1AF7

		//;test_61f14x_IR_Send.C: 332: SendBit++;
		INCR 	75H, 1H 		//00E7 	1AF5

		//;test_61f14x_IR_Send.C: 333: IRSendData = IRData[SendBit];
		LDR 	75H, 0H 			//00E8 	1875
		ADDWI 	20H 			//00E9 	0E20
		STR 	6H 			//00EA 	1086
		CLRF 	7H 			//00EB 	1187
		ORG		00ECH
		LDR 	1H, 0H 			//00EC 	1801
		STR 	78H 			//00ED 	10F8

		//;test_61f14x_IR_Send.C: 334: if (SendBit > 3)
		LDWI 	4H 			//00EE 	0004
		SUBWR 	75H, 0H 		//00EF 	1275
		BTSC 	3H, 0H 			//00F0 	2803

		//;test_61f14x_IR_Send.C: 335: {
		//;test_61f14x_IR_Send.C: 336: SendLastBit = 1;
		BSR 	7DH, 0H 			//00F1 	247D
		RET 					//00F2 	1008

		//;test_61f14x_IR_Send.C: 340: else
		//;test_61f14x_IR_Send.C: 341: {
		//;test_61f14x_IR_Send.C: 342: if(SendLastBit)
		BTSS 	7DH, 0H 		//00F3 	2C7D
		ORG		00F4H
		RET 					//00F4 	1008

		//;test_61f14x_IR_Send.C: 343: {
		//;test_61f14x_IR_Send.C: 344: TxTime++;
		INCR 	76H, 1H 		//00F5 	1AF6

		//;test_61f14x_IR_Send.C: 345: if(SaveLastBit)
		LDR 	72H, 0H 			//00F6 	1872
		BTSC 	3H, 2H 			//00F7 	2903
		LJUMP 	109H 			//00F8 	3909

		//;test_61f14x_IR_Send.C: 346: {
		//;test_61f14x_IR_Send.C: 347: if(TxTime < 3)
		LDWI 	3H 			//00F9 	0003
		SUBWR 	76H, 0H 		//00FA 	1276
		BTSS 	3H, 0H 			//00FB 	2C03
		ORG		00FCH
		LJUMP 	D2H 			//00FC 	38D2

		//;test_61f14x_IR_Send.C: 351: else if(TxTime < 4)
		LDWI 	4H 			//00FD 	0004
		SUBWR 	76H, 0H 		//00FE 	1276
		BTSS 	3H, 0H 			//00FF 	2C03
		LJUMP 	BFH 			//0100 	38BF

		//;test_61f14x_IR_Send.C: 355: else
		//;test_61f14x_IR_Send.C: 356: {
		//;test_61f14x_IR_Send.C: 357: T2UIE = 0;
		MOVLB 	6H 			//0101 	1026
		BCR 	DH, 0H 			//0102 	200D

		//;test_61f14x_IR_Send.C: 358: IRSendStatus = 0;
		CLRF 	79H 			//0103 	11F9
		ORG		0104H

		//;test_61f14x_IR_Send.C: 359: T2UIE = 0;
		BCR 	DH, 0H 			//0104 	200D

		//;test_61f14x_IR_Send.C: 360: SendLastBit = 0;
		BCR 	7DH, 0H 			//0105 	207D

		//;test_61f14x_IR_Send.C: 361: TxBit = 0;
		CLRF 	77H 			//0106 	11F7

		//;test_61f14x_IR_Send.C: 362: TxTime = 0;
		CLRF 	76H 			//0107 	11F6
		RET 					//0108 	1008

		//;test_61f14x_IR_Send.C: 365: else
		//;test_61f14x_IR_Send.C: 366: {
		//;test_61f14x_IR_Send.C: 367: if(TxTime < 5)
		LDWI 	5H 			//0109 	0005
		SUBWR 	76H, 0H 		//010A 	1276
		BTSS 	3H, 0H 			//010B 	2C03
		ORG		010CH
		LJUMP 	D2H 			//010C 	38D2

		//;test_61f14x_IR_Send.C: 371: else if(TxTime < 6)
		LDWI 	6H 			//010D 	0006
		LJUMP 	FEH 			//010E 	38FE
			END
