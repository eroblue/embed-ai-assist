//Deviec:FT61F14X
//-----------------------Variable---------------------------------
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2H 			//0001 	3802
		CLRF 	8H 			//0002 	1188
		MOVLP 	7H 			//0003 	0187
		LJUMP 	7A3H 			//0004 	3FA3
		ORG		07A3H
		MOVLB 	0H 			//07A3 	1020
		LJUMP 	7A5H 			//07A4 	3FA5

		//;test_61f14x_WDT.C: 117: POWER_INITIAL();
		LCALL 	7CEH 			//07A5 	37CE
		MOVLP 	7H 			//07A6 	0187

		//;test_61f14x_WDT.C: 118: WDT_INITIAL();
		LCALL 	7F0H 			//07A7 	37F0
		MOVLP 	7H 			//07A8 	0187

		//;test_61f14x_WDT.C: 119: INTCON = 0B11000000;
		LDWI 	C0H 			//07A9 	00C0
		STR 	BH 			//07AA 	108B
		ORG		07ABH

		//;test_61f14x_WDT.C: 120: PA0 = 1;
		MOVLB 	0H 			//07AB 	1020
		LDWI 	3H 			//07AC 	0003
		BSR 	CH, 0H 			//07AD 	240C

		//;test_61f14x_WDT.C: 121: DelayMs(3);
		LCALL 	7BDH 			//07AE 	37BD
		MOVLP 	7H 			//07AF 	0187

		//;test_61f14x_WDT.C: 122: PA0 = 0;
		MOVLB 	0H 			//07B0 	1020
		LDWI 	3H 			//07B1 	0003
		BCR 	CH, 0H 			//07B2 	200C
		ORG		07B3H

		//;test_61f14x_WDT.C: 123: DelayMs(3);
		LCALL 	7BDH 			//07B3 	37BD
		MOVLP 	7H 			//07B4 	0187

		//;test_61f14x_WDT.C: 125: {
		//;test_61f14x_WDT.C: 127: PA0 = 1;
		MOVLB 	0H 			//07B5 	1020
		LDWI 	1H 			//07B6 	0001
		BSR 	CH, 0H 			//07B7 	240C

		//;test_61f14x_WDT.C: 128: DelayMs(1);
		LCALL 	7BDH 			//07B8 	37BD
		MOVLP 	7H 			//07B9 	0187

		//;test_61f14x_WDT.C: 129: PA0 = 0;
		MOVLB 	0H 			//07BA 	1020
		ORG		07BBH
		LDWI 	1H 			//07BB 	0001
		LJUMP 	7B2H 			//07BC 	3FB2

		//;test_61f14x_WDT.C: 130: DelayMs(1);
		STR 	72H 			//07BD 	10F2

		//;test_61f14x_WDT.C: 88: unsigned char a,b;
		//;test_61f14x_WDT.C: 89: for(a=0;a<Time;a++)
		CLRF 	73H 			//07BE 	11F3
		LDR 	72H, 0H 			//07BF 	1872
		SUBWR 	73H, 0H 		//07C0 	1273
		BTSC 	3H, 0H 			//07C1 	2803
		RET 					//07C2 	1008
		ORG		07C3H

		//;test_61f14x_WDT.C: 90: {
		//;test_61f14x_WDT.C: 91: for(b=0;b<5;b++)
		CLRF 	74H 			//07C3 	11F4

		//;test_61f14x_WDT.C: 92: {
		//;test_61f14x_WDT.C: 93: DelayUs(197);
		LDWI 	C5H 			//07C4 	00C5
		LCALL 	7F7H 			//07C5 	37F7
		MOVLP 	7H 			//07C6 	0187
		LDWI 	5H 			//07C7 	0005
		INCR 	74H, 1H 		//07C8 	1AF4
		SUBWR 	74H, 0H 		//07C9 	1274
		BTSS 	3H, 0H 			//07CA 	2C03
		ORG		07CBH
		LJUMP 	7C4H 			//07CB 	3FC4
		INCR 	73H, 1H 		//07CC 	1AF3
		LJUMP 	7BFH 			//07CD 	3FBF

		//;test_61f14x_WDT.C: 39: OSCCON = 0B01110001;
		LDWI 	71H 			//07CE 	0071
		MOVLB 	1H 			//07CF 	1021
		STR 	19H 			//07D0 	1099

		//;test_61f14x_WDT.C: 40: INTCON = 0;
		CLRF 	BH 			//07D1 	118B

		//;test_61f14x_WDT.C: 42: PORTA = 0B00000000;
		MOVLB 	0H 			//07D2 	1020
		ORG		07D3H
		CLRF 	CH 			//07D3 	118C

		//;test_61f14x_WDT.C: 43: TRISA = 0B00000000;
		MOVLB 	1H 			//07D4 	1021
		CLRF 	CH 			//07D5 	118C

		//;test_61f14x_WDT.C: 44: PORTB = 0B00000000;
		MOVLB 	0H 			//07D6 	1020
		CLRF 	DH 			//07D7 	118D

		//;test_61f14x_WDT.C: 45: TRISB = 0B00000000;
		MOVLB 	1H 			//07D8 	1021
		CLRF 	DH 			//07D9 	118D

		//;test_61f14x_WDT.C: 46: PORTC = 0B00000000;
		MOVLB 	0H 			//07DA 	1020
		ORG		07DBH
		CLRF 	EH 			//07DB 	118E

		//;test_61f14x_WDT.C: 47: TRISC = 0B00000000;
		MOVLB 	1H 			//07DC 	1021
		CLRF 	EH 			//07DD 	118E

		//;test_61f14x_WDT.C: 49: WPUA = 0B00000000;
		MOVLB 	3H 			//07DE 	1023
		CLRF 	CH 			//07DF 	118C

		//;test_61f14x_WDT.C: 50: WPUB = 0B00000000;
		CLRF 	DH 			//07E0 	118D

		//;test_61f14x_WDT.C: 51: WPUC = 0B00000000;
		CLRF 	EH 			//07E1 	118E

		//;test_61f14x_WDT.C: 53: WPDA = 0B00000000;
		MOVLB 	4H 			//07E2 	1024
		ORG		07E3H
		CLRF 	CH 			//07E3 	118C

		//;test_61f14x_WDT.C: 54: WPDB = 0B00000000;
		CLRF 	DH 			//07E4 	118D

		//;test_61f14x_WDT.C: 55: WPDC = 0B00000000;
		CLRF 	EH 			//07E5 	118E

		//;test_61f14x_WDT.C: 57: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07E6 	00FF
		MOVLB 	2H 			//07E7 	1022
		STR 	1AH 			//07E8 	109A

		//;test_61f14x_WDT.C: 58: PSRC1 = 0B11111111;
		STR 	1BH 			//07E9 	109B

		//;test_61f14x_WDT.C: 60: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07EA 	1023
		ORG		07EBH
		STR 	1AH 			//07EB 	109A

		//;test_61f14x_WDT.C: 61: PSINK1 = 0B11111111;
		STR 	1BH 			//07EC 	109B

		//;test_61f14x_WDT.C: 62: PSINK2 = 0B11111111;
		STR 	1CH 			//07ED 	109C

		//;test_61f14x_WDT.C: 64: ANSELA = 0B00000000;
		CLRF 	17H 			//07EE 	1197
		RET 					//07EF 	1008
		CLRWDT 			//07F0 	1064

		//;test_61f14x_WDT.C: 106: MISC0 = 0B00000000;
		MOVLB 	3H 			//07F1 	1023
		CLRF 	1DH 			//07F2 	119D
		ORG		07F3H

		//;test_61f14x_WDT.C: 107: WDTCON = 0B00001011;
		LDWI 	BH 			//07F3 	000B
		MOVLB 	1H 			//07F4 	1021
		STR 	17H 			//07F5 	1097
		RET 					//07F6 	1008
		STR 	70H 			//07F7 	10F0

		//;test_61f14x_WDT.C: 74: unsigned char a;
		//;test_61f14x_WDT.C: 75: for(a=0;a<Time;a++)
		CLRF 	71H 			//07F8 	11F1
		LDR 	70H, 0H 			//07F9 	1870
		SUBWR 	71H, 0H 		//07FA 	1271
		ORG		07FBH
		BTSC 	3H, 0H 			//07FB 	2803
		RET 					//07FC 	1008

		//;test_61f14x_WDT.C: 76: {
		//;test_61f14x_WDT.C: 77: _nop();
		NOP 					//07FD 	1000
		INCR 	71H, 1H 		//07FE 	1AF1
		LJUMP 	7F9H 			//07FF 	3FF9
			END
