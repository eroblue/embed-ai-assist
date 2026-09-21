//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_receivedata		EQU		2BH
		_senddata		EQU		78H
		_receive_flag		EQU		77H
		_toSend		EQU		20H
		_i		EQU		75H
		_mmm		EQU		76H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2BH 			//0001 	382B
		ORG		0004H
		MOVLP 	0H 			//0004 	0180

		//;test_61f14x_USART.C: 41: if(URRXNE && RXNEF)
		MOVLB 	9H 			//0005 	1029
		BTSC 	EH, 0H 			//0006 	280E
		BTSS 	12H, 0H 		//0007 	2C12
		LJUMP 	17H 			//0008 	3817

		//;test_61f14x_USART.C: 42: {
		//;test_61f14x_USART.C: 43: receivedata[mmm++] =URDATAL;
		LDR 	76H, 0H 			//0009 	1876
		ADDWI 	2BH 			//000A 	0E2B
		STR 	6H 			//000B 	1086
		ORG		000CH
		CLRF 	7H 			//000C 	1187
		LDR 	CH, 0H 			//000D 	180C
		STR 	1H 			//000E 	1081
		INCR 	76H, 1H 		//000F 	1AF6

		//;test_61f14x_USART.C: 44: receive_flag = 1;
		CLRF 	77H 			//0010 	11F7
		INCR 	77H, 1H 		//0011 	1AF7

		//;test_61f14x_USART.C: 45: if(mmm>=10)
		LDWI 	AH 			//0012 	000A
		SUBWR 	76H, 0H 		//0013 	1276
		ORG		0014H
		BTSC 	3H, 0H 			//0014 	2803

		//;test_61f14x_USART.C: 46: {
		//;test_61f14x_USART.C: 47: mmm=0;
		CLRF 	76H 			//0015 	11F6

		//;test_61f14x_USART.C: 48: }
		//;test_61f14x_USART.C: 49: _nop();
		NOP 					//0016 	1000

		//;test_61f14x_USART.C: 50: }
		//;test_61f14x_USART.C: 52: if(TCEN && TCF)
		MOVLB 	9H 			//0017 	1029
		BTSC 	EH, 5H 			//0018 	2A8E
		BTSS 	1CH, 0H 		//0019 	2C1C
		RETI 					//001A 	1009
		LDWI 	AH 			//001B 	000A
		ORG		001CH

		//;test_61f14x_USART.C: 53: {
		//;test_61f14x_USART.C: 54: TCF=1;
		BSR 	1CH, 0H 			//001C 	241C

		//;test_61f14x_USART.C: 56: if(i<10)
		SUBWR 	75H, 0H 		//001D 	1275
		BTSC 	3H, 0H 			//001E 	2803
		LJUMP 	28H 			//001F 	3828

		//;test_61f14x_USART.C: 57: {
		//;test_61f14x_USART.C: 58: URDATAL =toSend[i++];
		LDR 	75H, 0H 			//0020 	1875
		ADDWI 	20H 			//0021 	0E20
		STR 	6H 			//0022 	1086
		CLRF 	7H 			//0023 	1187
		ORG		0024H
		LDR 	1H, 0H 			//0024 	1801
		STR 	CH 			//0025 	108C
		INCR 	75H, 1H 		//0026 	1AF5

		//;test_61f14x_USART.C: 59: }
		LJUMP 	29H 			//0027 	3829

		//;test_61f14x_USART.C: 60: else
		//;test_61f14x_USART.C: 61: {
		//;test_61f14x_USART.C: 62: i=0;
		CLRF 	75H 			//0028 	11F5

		//;test_61f14x_USART.C: 63: }
		//;test_61f14x_USART.C: 64: _nop();
		NOP 					//0029 	1000
		RETI 					//002A 	1009
		CLRF 	8H 			//002B 	1188
		ORG		002CH
		MOVLP 	0H 			//002C 	0180
		LJUMP 	2EH 			//002D 	382E
		LDWI 	11H 			//002E 	0011
		CLRF 	75H 			//002F 	11F5
		CLRF 	76H 			//0030 	11F6
		CLRF 	77H 			//0031 	11F7
		CLRF 	78H 			//0032 	11F8
		CLRF 	2BH 			//0033 	11AB
		ORG		0034H
		CLRF 	2CH 			//0034 	11AC
		CLRF 	2DH 			//0035 	11AD
		CLRF 	2EH 			//0036 	11AE
		CLRF 	2FH 			//0037 	11AF
		CLRF 	30H 			//0038 	11B0
		CLRF 	31H 			//0039 	11B1
		CLRF 	32H 			//003A 	11B2
		CLRF 	33H 			//003B 	11B3
		ORG		003CH
		CLRF 	34H 			//003C 	11B4
		STR 	20H 			//003D 	10A0
		LDWI 	22H 			//003E 	0022
		STR 	21H 			//003F 	10A1
		LDWI 	33H 			//0040 	0033
		STR 	22H 			//0041 	10A2
		LDWI 	44H 			//0042 	0044
		STR 	23H 			//0043 	10A3
		ORG		0044H
		LDWI 	55H 			//0044 	0055
		STR 	24H 			//0045 	10A4
		LDWI 	66H 			//0046 	0066
		STR 	25H 			//0047 	10A5
		LDWI 	77H 			//0048 	0077
		STR 	26H 			//0049 	10A6
		LDWI 	88H 			//004A 	0088
		STR 	27H 			//004B 	10A7
		ORG		004CH
		LDWI 	99H 			//004C 	0099
		STR 	28H 			//004D 	10A8
		LDWI 	AAH 			//004E 	00AA
		STR 	29H 			//004F 	10A9
		LDWI 	0H 			//0050 	0000
		STR 	2AH 			//0051 	10AA
		MOVLB 	0H 			//0052 	1020
		LJUMP 	54H 			//0053 	3854
		ORG		0054H

		//;test_61f14x_USART.C: 164: POWER_INITIAL();
		LCALL 	7AH 			//0054 	307A
		MOVLP 	0H 			//0055 	0180

		//;test_61f14x_USART.C: 165: UART_INITIAL();
		LCALL 	9DH 			//0056 	309D
		MOVLP 	0H 			//0057 	0180

		//;test_61f14x_USART.C: 166: DelayMs(100);
		LDWI 	64H 			//0058 	0064
		LCALL 	69H 			//0059 	3069
		MOVLP 	0H 			//005A 	0180

		//;test_61f14x_USART.C: 168: if(TXEF)
		MOVLB 	9H 			//005B 	1029
		ORG		005CH
		BTSS 	12H, 5H 		//005C 	2E92
		LJUMP 	61H 			//005D 	3861

		//;test_61f14x_USART.C: 169: {
		//;test_61f14x_USART.C: 170: URDATAL =0xaa;
		LDWI 	AAH 			//005E 	00AA
		MOVLB 	9H 			//005F 	1029
		STR 	CH 			//0060 	108C

		//;test_61f14x_USART.C: 174: {
		//;test_61f14x_USART.C: 175: _nop();
		NOP 					//0061 	1000

		//;test_61f14x_USART.C: 176: DelayMs(250);
		LDWI 	FAH 			//0062 	00FA
		LCALL 	69H 			//0063 	3069
		ORG		0064H
		MOVLP 	0H 			//0064 	0180

		//;test_61f14x_USART.C: 178: if(receive_flag == 1)
		DECRSZ 	77H, 0H 		//0065 	1B77
		LJUMP 	61H 			//0066 	3861

		//;test_61f14x_USART.C: 179: {
		//;test_61f14x_USART.C: 180: receive_flag = 0;
		CLRF 	77H 			//0067 	11F7
		LJUMP 	5EH 			//0068 	385E
		STR 	72H 			//0069 	10F2

		//;test_61f14x_USART.C: 124: unsigned char a,b;
		//;test_61f14x_USART.C: 125: for(a=0;a<Time;a++)
		CLRF 	73H 			//006A 	11F3
		LDR 	72H, 0H 			//006B 	1872
		ORG		006CH
		SUBWR 	73H, 0H 		//006C 	1273
		BTSC 	3H, 0H 			//006D 	2803
		RET 					//006E 	1008

		//;test_61f14x_USART.C: 126: {
		//;test_61f14x_USART.C: 127: for(b=0;b<5;b++)
		CLRF 	74H 			//006F 	11F4

		//;test_61f14x_USART.C: 128: {
		//;test_61f14x_USART.C: 129: DelayUs(197);
		LDWI 	C5H 			//0070 	00C5
		LCALL 	ADH 			//0071 	30AD
		MOVLP 	0H 			//0072 	0180
		LDWI 	5H 			//0073 	0005
		ORG		0074H
		INCR 	74H, 1H 		//0074 	1AF4
		SUBWR 	74H, 0H 		//0075 	1274
		BTSS 	3H, 0H 			//0076 	2C03
		LJUMP 	70H 			//0077 	3870
		INCR 	73H, 1H 		//0078 	1AF3
		LJUMP 	6BH 			//0079 	386B

		//;test_61f14x_USART.C: 75: OSCCON = 0B01110001;
		LDWI 	71H 			//007A 	0071
		MOVLB 	1H 			//007B 	1021
		ORG		007CH
		STR 	19H 			//007C 	1099

		//;test_61f14x_USART.C: 76: INTCON = 0;
		CLRF 	BH 			//007D 	118B

		//;test_61f14x_USART.C: 78: PORTA = 0B00000000;
		MOVLB 	0H 			//007E 	1020
		CLRF 	CH 			//007F 	118C

		//;test_61f14x_USART.C: 79: TRISA = 0B10000000;
		LDWI 	80H 			//0080 	0080
		MOVLB 	1H 			//0081 	1021
		STR 	CH 			//0082 	108C

		//;test_61f14x_USART.C: 80: PORTB = 0B00000000;
		MOVLB 	0H 			//0083 	1020
		ORG		0084H
		CLRF 	DH 			//0084 	118D

		//;test_61f14x_USART.C: 81: TRISB = 0B00000000;
		MOVLB 	1H 			//0085 	1021
		CLRF 	DH 			//0086 	118D

		//;test_61f14x_USART.C: 82: PORTC = 0B00000000;
		MOVLB 	0H 			//0087 	1020
		CLRF 	EH 			//0088 	118E

		//;test_61f14x_USART.C: 83: TRISC = 0B00000000;
		MOVLB 	1H 			//0089 	1021
		CLRF 	EH 			//008A 	118E

		//;test_61f14x_USART.C: 85: WPUA = 0B00000000;
		MOVLB 	3H 			//008B 	1023
		ORG		008CH
		CLRF 	CH 			//008C 	118C

		//;test_61f14x_USART.C: 86: WPUB = 0B00000000;
		CLRF 	DH 			//008D 	118D

		//;test_61f14x_USART.C: 87: WPUC = 0B00000000;
		CLRF 	EH 			//008E 	118E

		//;test_61f14x_USART.C: 89: WPDA = 0B10000000;
		MOVLB 	4H 			//008F 	1024
		STR 	CH 			//0090 	108C

		//;test_61f14x_USART.C: 90: WPDB = 0B00000000;
		CLRF 	DH 			//0091 	118D

		//;test_61f14x_USART.C: 91: WPDC = 0B00000000;
		CLRF 	EH 			//0092 	118E

		//;test_61f14x_USART.C: 93: PSRC0 = 0B11111111;
		LDWI 	FFH 			//0093 	00FF
		ORG		0094H
		MOVLB 	2H 			//0094 	1022
		STR 	1AH 			//0095 	109A

		//;test_61f14x_USART.C: 94: PSRC1 = 0B11111111;
		STR 	1BH 			//0096 	109B

		//;test_61f14x_USART.C: 96: PSINK0 = 0B11111111;
		MOVLB 	3H 			//0097 	1023
		STR 	1AH 			//0098 	109A

		//;test_61f14x_USART.C: 97: PSINK1 = 0B11111111;
		STR 	1BH 			//0099 	109B

		//;test_61f14x_USART.C: 98: PSINK2 = 0B11111111;
		STR 	1CH 			//009A 	109C

		//;test_61f14x_USART.C: 100: ANSELA = 0B00000000;
		CLRF 	17H 			//009B 	1197
		ORG		009CH
		RET 					//009C 	1008

		//;test_61f14x_USART.C: 141: PCKEN |=0B00100000;
		MOVLB 	1H 			//009D 	1021
		BSR 	1AH, 5H 			//009E 	269A

		//;test_61f14x_USART.C: 143: URIER =0B00100001;
		LDWI 	21H 			//009F 	0021
		MOVLB 	9H 			//00A0 	1029
		STR 	EH 			//00A1 	108E

		//;test_61f14x_USART.C: 144: URLCR =0B00000001;
		LDWI 	1H 			//00A2 	0001
		STR 	FH 			//00A3 	108F
		ORG		00A4H

		//;test_61f14x_USART.C: 145: URMCR =0B00011000;
		LDWI 	18H 			//00A4 	0018
		STR 	11H 			//00A5 	1091

		//;test_61f14x_USART.C: 147: URDLL =104;
		LDWI 	68H 			//00A6 	0068
		STR 	14H 			//00A7 	1094

		//;test_61f14x_USART.C: 148: URDLH =0;
		CLRF 	15H 			//00A8 	1195
		LDWI 	C0H 			//00A9 	00C0

		//;test_61f14x_USART.C: 149: TCF=1;
		BSR 	1CH, 0H 			//00AA 	241C

		//;test_61f14x_USART.C: 150: INTCON=0B11000000;
		STR 	BH 			//00AB 	108B
		ORG		00ACH
		RET 					//00AC 	1008
		STR 	70H 			//00AD 	10F0

		//;test_61f14x_USART.C: 110: unsigned char a;
		//;test_61f14x_USART.C: 111: for(a=0;a<Time;a++)
		CLRF 	71H 			//00AE 	11F1
		LDR 	70H, 0H 			//00AF 	1870
		SUBWR 	71H, 0H 		//00B0 	1271
		BTSC 	3H, 0H 			//00B1 	2803
		RET 					//00B2 	1008

		//;test_61f14x_USART.C: 112: {
		//;test_61f14x_USART.C: 113: _nop();
		NOP 					//00B3 	1000
		ORG		00B4H
		INCR 	71H, 1H 		//00B4 	1AF1
		LJUMP 	AFH 			//00B5 	38AF
			END
