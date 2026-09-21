//Deviec:FT61F14X
//-----------------------Variable---------------------------------
//		DelayMs@Time		EQU		72H
//		DelayMs@b		EQU		74H
//		DelayMs@a		EQU		73H
//		DelayMs@Time		EQU		C00000H
//		DelayUs@Time		EQU		70H
//		DelayUs@a		EQU		71H
//		DelayUs@Time		EQU		C00000H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2H 			//0001 	3802
		MOVLP 	7H 			//0002 	0187
		LJUMP 	7B3H 			//0003 	3FB3
		ORG		07B3H
		MOVLB 	0H 			//07B3 	1020
		LJUMP 	7B5H 			//07B4 	3FB5

		//;test_61f14x_IO.C: 108: POWER_INITIAL();
		LCALL 	7DDH 			//07B5 	37DD
		MOVLP 	7H 			//07B6 	0187

		//;test_61f14x_IO.C: 110: {
		//;test_61f14x_IO.C: 111: PB3 = 1;
		MOVLB 	0H 			//07B7 	1020
		BSR 	DH, 3H 			//07B8 	258D

		//;test_61f14x_IO.C: 112: DelayMs(10);
		LDWI 	AH 			//07B9 	000A
		LCALL 	7C3H 			//07BA 	37C3
		ORG		07BBH
		MOVLP 	7H 			//07BB 	0187

		//;test_61f14x_IO.C: 113: if(PC0 == 1)
		MOVLB 	0H 			//07BC 	1020
		BTSC 	EH, 0H 			//07BD 	280E

		//;test_61f14x_IO.C: 114: {
		//;test_61f14x_IO.C: 115: PB3 = 0;
		BCR 	DH, 3H 			//07BE 	218D

		//;test_61f14x_IO.C: 116: }
		//;test_61f14x_IO.C: 117: DelayMs(10);
		LDWI 	AH 			//07BF 	000A
		LCALL 	7C3H 			//07C0 	37C3
		MOVLP 	7H 			//07C1 	0187
		LJUMP 	7B7H 			//07C2 	3FB7
		ORG		07C3H
		STR 	72H 			//07C3 	10F2

		//;test_61f14x_IO.C: 91: unsigned char a,b;
		//;test_61f14x_IO.C: 92: for(a=0;a<Time;a++)
		CLRF 	73H 			//07C4 	11F3
		LDR 	72H, 0H 			//07C5 	1872
		SUBWR 	73H, 0H 		//07C6 	1273
		BTSC 	3H, 0H 			//07C7 	2803
		RET 					//07C8 	1008

		//;test_61f14x_IO.C: 93: {
		//;test_61f14x_IO.C: 94: for(b=0;b<5;b++)
		CLRF 	74H 			//07C9 	11F4

		//;test_61f14x_IO.C: 95: {
		//;test_61f14x_IO.C: 96: DelayUs(197);
		LDWI 	C5H 			//07CA 	00C5
		ORG		07CBH
		LCALL 	7D4H 			//07CB 	37D4
		MOVLP 	7H 			//07CC 	0187
		LDWI 	5H 			//07CD 	0005
		INCR 	74H, 1H 		//07CE 	1AF4
		SUBWR 	74H, 0H 		//07CF 	1274
		BTSS 	3H, 0H 			//07D0 	2C03
		LJUMP 	7CAH 			//07D1 	3FCA
		INCR 	73H, 1H 		//07D2 	1AF3
		ORG		07D3H
		LJUMP 	7C5H 			//07D3 	3FC5
		STR 	70H 			//07D4 	10F0

		//;test_61f14x_IO.C: 77: unsigned char a;
		//;test_61f14x_IO.C: 78: for(a=0;a<Time;a++)
		CLRF 	71H 			//07D5 	11F1
		LDR 	70H, 0H 			//07D6 	1870
		SUBWR 	71H, 0H 		//07D7 	1271
		BTSC 	3H, 0H 			//07D8 	2803
		RET 					//07D9 	1008

		//;test_61f14x_IO.C: 79: {
		//;test_61f14x_IO.C: 80: __nop();
		NOP 					//07DA 	1000
		ORG		07DBH
		INCR 	71H, 1H 		//07DB 	1AF1
		LJUMP 	7D6H 			//07DC 	3FD6

		//;test_61f14x_IO.C: 42: OSCCON = 0B01110001;
		LDWI 	71H 			//07DD 	0071
		MOVLB 	1H 			//07DE 	1021
		STR 	19H 			//07DF 	1099

		//;test_61f14x_IO.C: 43: INTCON = 0;
		CLRF 	BH 			//07E0 	118B

		//;test_61f14x_IO.C: 45: PORTA = 0B00000000;
		MOVLB 	0H 			//07E1 	1020
		CLRF 	CH 			//07E2 	118C
		ORG		07E3H

		//;test_61f14x_IO.C: 46: TRISA = 0B00000000;
		MOVLB 	1H 			//07E3 	1021
		CLRF 	CH 			//07E4 	118C

		//;test_61f14x_IO.C: 47: PORTB = 0B00000000;
		MOVLB 	0H 			//07E5 	1020
		CLRF 	DH 			//07E6 	118D

		//;test_61f14x_IO.C: 48: TRISB = 0B00000000;
		MOVLB 	1H 			//07E7 	1021
		CLRF 	DH 			//07E8 	118D

		//;test_61f14x_IO.C: 49: PORTC = 0B00000000;
		MOVLB 	0H 			//07E9 	1020
		CLRF 	EH 			//07EA 	118E
		ORG		07EBH

		//;test_61f14x_IO.C: 50: TRISC = 0B00000001;
		LDWI 	1H 			//07EB 	0001
		MOVLB 	1H 			//07EC 	1021
		STR 	EH 			//07ED 	108E

		//;test_61f14x_IO.C: 52: WPUA = 0B00000000;
		MOVLB 	3H 			//07EE 	1023
		CLRF 	CH 			//07EF 	118C

		//;test_61f14x_IO.C: 53: WPUB = 0B00000000;
		CLRF 	DH 			//07F0 	118D

		//;test_61f14x_IO.C: 54: WPUC = 0B00000001;
		STR 	EH 			//07F1 	108E

		//;test_61f14x_IO.C: 56: WPDA = 0B00000000;
		MOVLB 	4H 			//07F2 	1024
		ORG		07F3H
		CLRF 	CH 			//07F3 	118C

		//;test_61f14x_IO.C: 57: WPDB = 0B00000000;
		CLRF 	DH 			//07F4 	118D

		//;test_61f14x_IO.C: 58: WPDC = 0B00000000;
		CLRF 	EH 			//07F5 	118E

		//;test_61f14x_IO.C: 60: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07F6 	00FF
		MOVLB 	2H 			//07F7 	1022
		STR 	1AH 			//07F8 	109A

		//;test_61f14x_IO.C: 61: PSRC1 = 0B11111111;
		STR 	1BH 			//07F9 	109B

		//;test_61f14x_IO.C: 63: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07FA 	1023
		ORG		07FBH
		STR 	1AH 			//07FB 	109A

		//;test_61f14x_IO.C: 64: PSINK1 = 0B11111111;
		STR 	1BH 			//07FC 	109B

		//;test_61f14x_IO.C: 65: PSINK2 = 0B11111111;
		STR 	1CH 			//07FD 	109C

		//;test_61f14x_IO.C: 67: ANSELA = 0B00000000;
		CLRF 	17H 			//07FE 	1197
		RET 					//07FF 	1008
			END
