//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_IRbitNum		EQU		78H
		_IRbitTime		EQU		77H
		_IRDataTimer		EQU		70H
		_bitdata		EQU		79H
		_ReceiveFinish		EQU		76H
		_rdata1		EQU		75H
		_rdata2		EQU		74H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	41H 			//0001 	3841
		ORG		0004H
		BSR 	7EH, 0H 			//0004 	247E
		MOVLP 	0H 			//0005 	0180

		//;test_61f14x_IR_Receive.C: 183: if(T4UIE && T4UIF)
		MOVLB 	2H 			//0006 	1022
		BTSC 	12H, 0H 		//0007 	2812
		BTSS 	13H, 0H 		//0008 	2C13
		LJUMP 	12H 			//0009 	3812

		//;test_61f14x_IR_Receive.C: 184: {
		//;test_61f14x_IR_Receive.C: 185: T4UIF = 1;
		BSR 	13H, 0H 			//000A 	2413
		LDWI 	33H 			//000B 	0033
		ORG		000CH

		//;test_61f14x_IR_Receive.C: 187: IRbitTime++;
		INCR 	77H, 1H 		//000C 	1AF7

		//;test_61f14x_IR_Receive.C: 188: if(IRbitTime > 50)
		SUBWR 	77H, 0H 		//000D 	1277
		BTSS 	3H, 0H 			//000E 	2C03
		LJUMP 	12H 			//000F 	3812

		//;test_61f14x_IR_Receive.C: 189: {
		//;test_61f14x_IR_Receive.C: 190: T4UIE = 0;
		BCR 	12H, 0H 			//0010 	2012

		//;test_61f14x_IR_Receive.C: 191: IRbitTime = 0;
		CLRF 	77H 			//0011 	11F7

		//;test_61f14x_IR_Receive.C: 192: }
		//;test_61f14x_IR_Receive.C: 193: }
		//;test_61f14x_IR_Receive.C: 196: if(EPIF0 & 0x08)
		MOVLB 	0H 			//0012 	1020
		BTSS 	14H, 3H 		//0013 	2D94
		ORG		0014H
		LJUMP 	3FH 			//0014 	383F

		//;test_61f14x_IR_Receive.C: 197: {
		//;test_61f14x_IR_Receive.C: 198: EPIF0 |= 0x08;
		BSR 	14H, 3H 			//0015 	2594

		//;test_61f14x_IR_Receive.C: 200: if(PC1 == 0)
		BTSC 	EH, 1H 			//0016 	288E
		LJUMP 	3FH 			//0017 	383F

		//;test_61f14x_IR_Receive.C: 201: {
		//;test_61f14x_IR_Receive.C: 202: T4UIE = 1;
		MOVLB 	2H 			//0018 	1022
		BSR 	12H, 0H 			//0019 	2412

		//;test_61f14x_IR_Receive.C: 203: if(IRbitTime > 21)
		LDWI 	16H 			//001A 	0016
		SUBWR 	77H, 0H 		//001B 	1277
		ORG		001CH
		BTSS 	3H, 0H 			//001C 	2C03
		LJUMP 	25H 			//001D 	3825

		//;test_61f14x_IR_Receive.C: 204: {
		//;test_61f14x_IR_Receive.C: 205: IRDataTimer[0] = 0;
		CLRF 	70H 			//001E 	11F0

		//;test_61f14x_IR_Receive.C: 206: IRDataTimer[1] = 0;
		CLRF 	71H 			//001F 	11F1

		//;test_61f14x_IR_Receive.C: 207: IRDataTimer[2] = 0;
		CLRF 	72H 			//0020 	11F2

		//;test_61f14x_IR_Receive.C: 208: IRDataTimer[3] = 0;
		CLRF 	73H 			//0021 	11F3

		//;test_61f14x_IR_Receive.C: 209: IRbitNum = 0;
		CLRF 	78H 			//0022 	11F8

		//;test_61f14x_IR_Receive.C: 210: bitdata = 0x00;
		CLRF 	79H 			//0023 	11F9
		ORG		0024H

		//;test_61f14x_IR_Receive.C: 211: }
		LJUMP 	2FH 			//0024 	382F

		//;test_61f14x_IR_Receive.C: 212: else if(IRbitTime > 3)
		LDWI 	4H 			//0025 	0004
		SUBWR 	77H, 0H 		//0026 	1277
		BTSS 	3H, 0H 			//0027 	2C03
		LJUMP 	2FH 			//0028 	382F

		//;test_61f14x_IR_Receive.C: 213: {
		//;test_61f14x_IR_Receive.C: 214: IRDataTimer[IRbitNum-1] |= bitdata;
		LDR 	78H, 0H 			//0029 	1878
		ADDWI 	6FH 			//002A 	0E6F
		STR 	6H 			//002B 	1086
		ORG		002CH
		CLRF 	7H 			//002C 	1187
		LDR 	79H, 0H 			//002D 	1879
		IORWR 	1H, 1H 		//002E 	1481

		//;test_61f14x_IR_Receive.C: 215: }
		//;test_61f14x_IR_Receive.C: 216: IRbitTime = 0;
		CLRF 	77H 			//002F 	11F7

		//;test_61f14x_IR_Receive.C: 217: bitdata<<=1;
		LSLF 	79H, 1H 		//0030 	05F9

		//;test_61f14x_IR_Receive.C: 218: if(bitdata == 0)
		LDR 	79H, 0H 			//0031 	1879
		BTSS 	3H, 2H 			//0032 	2D03
		LJUMP 	37H 			//0033 	3837
		ORG		0034H

		//;test_61f14x_IR_Receive.C: 219: {
		//;test_61f14x_IR_Receive.C: 220: bitdata = 0x01;
		CLRF 	79H 			//0034 	11F9
		INCR 	79H, 1H 		//0035 	1AF9

		//;test_61f14x_IR_Receive.C: 221: IRbitNum++;
		INCR 	78H, 1H 		//0036 	1AF8

		//;test_61f14x_IR_Receive.C: 222: }
		//;test_61f14x_IR_Receive.C: 223: if(IRbitNum > 4)
		LDWI 	5H 			//0037 	0005
		SUBWR 	78H, 0H 		//0038 	1278
		BTSS 	3H, 0H 			//0039 	2C03
		LJUMP 	3FH 			//003A 	383F

		//;test_61f14x_IR_Receive.C: 224: {
		//;test_61f14x_IR_Receive.C: 225: IRbitNum = 0;
		CLRF 	78H 			//003B 	11F8
		ORG		003CH

		//;test_61f14x_IR_Receive.C: 226: T4UIE = 0;
		BCR 	12H, 0H 			//003C 	2012

		//;test_61f14x_IR_Receive.C: 227: ReceiveFinish = 1;
		CLRF 	76H 			//003D 	11F6
		INCR 	76H, 1H 		//003E 	1AF6
		BCR 	7EH, 0H 			//003F 	207E
		RETI 					//0040 	1009
		MOVLP 	0H 			//0041 	0180
		LJUMP 	43H 			//0042 	3843
		LDWI 	1H 			//0043 	0001
		ORG		0044H
		STR 	79H 			//0044 	10F9
		CLRF 	70H 			//0045 	11F0
		CLRF 	71H 			//0046 	11F1
		CLRF 	72H 			//0047 	11F2
		CLRF 	73H 			//0048 	11F3
		CLRF 	74H 			//0049 	11F4
		CLRF 	75H 			//004A 	11F5
		CLRF 	76H 			//004B 	11F6
		ORG		004CH
		CLRF 	77H 			//004C 	11F7
		CLRF 	78H 			//004D 	11F8
		BCR 	7EH, 0H 			//004E 	207E
		MOVLB 	0H 			//004F 	1020
		LJUMP 	51H 			//0050 	3851

		//;test_61f14x_IR_Receive.C: 241: POWER_INITIAL();
		LCALL 	6BH 			//0051 	306B
		MOVLP 	0H 			//0052 	0180

		//;test_61f14x_IR_Receive.C: 242: TIMER4_INITIAL();
		LCALL 	9DH 			//0053 	309D
		ORG		0054H
		MOVLP 	0H 			//0054 	0180

		//;test_61f14x_IR_Receive.C: 243: Px_Level_Change_INITIAL();
		LCALL 	91H 			//0055 	3091
		MOVLP 	0H 			//0056 	0180

		//;test_61f14x_IR_Receive.C: 244: GIE = 1;
		BSR 	BH, 7H 			//0057 	278B

		//;test_61f14x_IR_Receive.C: 247: {
		//;test_61f14x_IR_Receive.C: 248: if(ReceiveFinish==1)
		DECRSZ 	76H, 0H 		//0058 	1B76
		LJUMP 	58H 			//0059 	3858

		//;test_61f14x_IR_Receive.C: 249: {
		//;test_61f14x_IR_Receive.C: 250: ReceiveFinish = 0;
		CLRF 	76H 			//005A 	11F6

		//;test_61f14x_IR_Receive.C: 251: rdata1 = 0xFF - IRDataTimer[0];
		COMR 	70H, 0H 		//005B 	1970
		ORG		005CH
		STR 	75H 			//005C 	10F5

		//;test_61f14x_IR_Receive.C: 252: rdata2 = 0xFF - IRDataTimer[2];
		COMR 	72H, 0H 		//005D 	1972
		STR 	74H 			//005E 	10F4

		//;test_61f14x_IR_Receive.C: 253: if((rdata1 == IRDataTimer[1])&&(rdata2 == IRDataTimer[3]
		//+                          ))
		LDR 	71H, 0H 			//005F 	1871
		XORWR 	75H, 0H 		//0060 	1675
		BTSS 	3H, 2H 			//0061 	2D03
		LJUMP 	58H 			//0062 	3858
		LDR 	73H, 0H 			//0063 	1873
		ORG		0064H
		XORWR 	74H, 0H 		//0064 	1674
		BTSS 	3H, 2H 			//0065 	2D03
		LJUMP 	58H 			//0066 	3858

		//;test_61f14x_IR_Receive.C: 254: {
		//;test_61f14x_IR_Receive.C: 255: PB3 = ~PB3;
		LDWI 	8H 			//0067 	0008
		MOVLB 	0H 			//0068 	1020
		XORWR 	DH, 1H 		//0069 	168D
		LJUMP 	58H 			//006A 	3858

		//;test_61f14x_IR_Receive.C: 48: OSCCON = 0B01110001;
		LDWI 	71H 			//006B 	0071
		ORG		006CH
		MOVLB 	1H 			//006C 	1021
		STR 	19H 			//006D 	1099

		//;test_61f14x_IR_Receive.C: 51: INTCON = 0;
		CLRF 	BH 			//006E 	118B

		//;test_61f14x_IR_Receive.C: 53: PORTA = 0B00000000;
		MOVLB 	0H 			//006F 	1020
		CLRF 	CH 			//0070 	118C

		//;test_61f14x_IR_Receive.C: 54: TRISA = 0B11111111;
		LDWI 	FFH 			//0071 	00FF
		MOVLB 	1H 			//0072 	1021
		STR 	CH 			//0073 	108C
		ORG		0074H

		//;test_61f14x_IR_Receive.C: 55: PORTB = 0B00000000;
		MOVLB 	0H 			//0074 	1020
		CLRF 	DH 			//0075 	118D

		//;test_61f14x_IR_Receive.C: 56: TRISB = 0B11110111;
		LDWI 	F7H 			//0076 	00F7
		MOVLB 	1H 			//0077 	1021
		STR 	DH 			//0078 	108D

		//;test_61f14x_IR_Receive.C: 57: PORTC = 0B00000000;
		MOVLB 	0H 			//0079 	1020
		CLRF 	EH 			//007A 	118E

		//;test_61f14x_IR_Receive.C: 58: TRISC = 0B11111111;
		LDWI 	FFH 			//007B 	00FF
		ORG		007CH
		MOVLB 	1H 			//007C 	1021
		STR 	EH 			//007D 	108E

		//;test_61f14x_IR_Receive.C: 60: WPUA = 0B00000000;
		MOVLB 	3H 			//007E 	1023
		CLRF 	CH 			//007F 	118C

		//;test_61f14x_IR_Receive.C: 61: WPUB = 0B00000000;
		CLRF 	DH 			//0080 	118D

		//;test_61f14x_IR_Receive.C: 62: WPUC = 0B00000010;
		LDWI 	2H 			//0081 	0002
		STR 	EH 			//0082 	108E

		//;test_61f14x_IR_Receive.C: 64: WPDA = 0B00000000;
		MOVLB 	4H 			//0083 	1024
		ORG		0084H
		CLRF 	CH 			//0084 	118C

		//;test_61f14x_IR_Receive.C: 65: WPDB = 0B00000000;
		CLRF 	DH 			//0085 	118D

		//;test_61f14x_IR_Receive.C: 66: WPDC = 0B00000000;
		CLRF 	EH 			//0086 	118E

		//;test_61f14x_IR_Receive.C: 68: PSRC0 = 0B11111111;
		LDWI 	FFH 			//0087 	00FF
		MOVLB 	2H 			//0088 	1022
		STR 	1AH 			//0089 	109A

		//;test_61f14x_IR_Receive.C: 72: PSRC1 = 0B11111111;
		STR 	1BH 			//008A 	109B

		//;test_61f14x_IR_Receive.C: 76: PSINK0 = 0B11111111;
		MOVLB 	3H 			//008B 	1023
		ORG		008CH
		STR 	1AH 			//008C 	109A

		//;test_61f14x_IR_Receive.C: 77: PSINK1 = 0B11111111;
		STR 	1BH 			//008D 	109B

		//;test_61f14x_IR_Receive.C: 78: PSINK2 = 0B11111111;
		STR 	1CH 			//008E 	109C

		//;test_61f14x_IR_Receive.C: 80: ANSELA = 0B00000000;
		CLRF 	17H 			//008F 	1197
		RET 					//0090 	1008

		//;test_61f14x_IR_Receive.C: 161: EPS0=0B10000000;
		LDWI 	80H 			//0091 	0080
		STR 	18H 			//0092 	1098

		//;test_61f14x_IR_Receive.C: 163: EPS1=0B00000000;
		CLRF 	19H 			//0093 	1199
		ORG		0094H

		//;test_61f14x_IR_Receive.C: 166: ITYPE0 = 0B11000000;
		LDWI 	C0H 			//0094 	00C0
		STR 	1EH 			//0095 	109E

		//;test_61f14x_IR_Receive.C: 167: ITYPE1 = 0B00000000;
		CLRF 	1FH 			//0096 	119F

		//;test_61f14x_IR_Receive.C: 169: EPIE0 = 0B00001000;
		LDWI 	8H 			//0097 	0008
		MOVLB 	1H 			//0098 	1021
		STR 	14H 			//0099 	1094

		//;test_61f14x_IR_Receive.C: 171: INTCON = 0B01000000;
		LDWI 	40H 			//009A 	0040
		STR 	BH 			//009B 	108B
		ORG		009CH
		RET 					//009C 	1008

		//;test_61f14x_IR_Receive.C: 91: PCKEN |=0B00001000;
		MOVLB 	1H 			//009D 	1021
		BSR 	1AH, 3H 			//009E 	259A

		//;test_61f14x_IR_Receive.C: 93: TIM4CR1 =0B00000101;
		LDWI 	5H 			//009F 	0005
		MOVLB 	2H 			//00A0 	1022
		STR 	11H 			//00A1 	1091

		//;test_61f14x_IR_Receive.C: 124: TIM4IER =0B00000001;
		LDWI 	1H 			//00A2 	0001
		STR 	12H 			//00A3 	1092
		ORG		00A4H

		//;test_61f14x_IR_Receive.C: 127: TIM4SR =0B00000000;
		CLRF 	13H 			//00A4 	1193

		//;test_61f14x_IR_Receive.C: 136: TIM4EGR =0B00000000;
		CLRF 	14H 			//00A5 	1194

		//;test_61f14x_IR_Receive.C: 141: TIM4CNTR=0;
		CLRF 	15H 			//00A6 	1195

		//;test_61f14x_IR_Receive.C: 143: TIM4PSCR=0B00000110;
		LDWI 	6H 			//00A7 	0006
		STR 	16H 			//00A8 	1096

		//;test_61f14x_IR_Receive.C: 148: TIM4ARR =140;
		LDWI 	8CH 			//00A9 	008C
		STR 	17H 			//00AA 	1097
		RET 					//00AB 	1008
			END
