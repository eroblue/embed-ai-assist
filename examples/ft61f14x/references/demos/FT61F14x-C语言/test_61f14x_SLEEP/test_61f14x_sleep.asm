//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_outputcounter		EQU		75H
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
		LJUMP 	7ABH 			//0003 	3FAB
		ORG		07ABH
		CLRF 	75H 			//07AB 	11F5
		MOVLB 	0H 			//07AC 	1020
		LJUMP 	7AEH 			//07AD 	3FAE

		//;test_61f14x_SLEEP.C: 105: POWER_INITIAL();
		LCALL 	7DEH 			//07AE 	37DE
		MOVLP 	7H 			//07AF 	0187

		//;test_61f14x_SLEEP.C: 107: {
		//;test_61f14x_SLEEP.C: 108: PB3 = 1;
		MOVLB 	0H 			//07B0 	1020
		BSR 	DH, 3H 			//07B1 	258D

		//;test_61f14x_SLEEP.C: 109: DelayMs(10);
		LDWI 	AH 			//07B2 	000A
		ORG		07B3H
		LCALL 	7C4H 			//07B3 	37C4
		MOVLP 	7H 			//07B4 	0187

		//;test_61f14x_SLEEP.C: 110: PB3 = 0;
		MOVLB 	0H 			//07B5 	1020
		BCR 	DH, 3H 			//07B6 	218D

		//;test_61f14x_SLEEP.C: 111: DelayMs(10);
		LDWI 	AH 			//07B7 	000A
		LCALL 	7C4H 			//07B8 	37C4
		MOVLP 	7H 			//07B9 	0187

		//;test_61f14x_SLEEP.C: 113: if(++outputcounter>100)
		LDWI 	65H 			//07BA 	0065
		ORG		07BBH
		INCR 	75H, 1H 		//07BB 	1AF5
		SUBWR 	75H, 0H 		//07BC 	1275
		BTSS 	3H, 0H 			//07BD 	2C03
		LJUMP 	7B0H 			//07BE 	3FB0

		//;test_61f14x_SLEEP.C: 114: {
		//;test_61f14x_SLEEP.C: 115: outputcounter=0;
		CLRF 	75H 			//07BF 	11F5
		SLEEP 					//07C0 	1063

		//;test_61f14x_SLEEP.C: 118: __nop();
		NOP 					//07C1 	1000

		//;test_61f14x_SLEEP.C: 119: __nop();
		NOP 					//07C2 	1000
		ORG		07C3H
		LJUMP 	7B0H 			//07C3 	3FB0
		STR 	72H 			//07C4 	10F2

		//;test_61f14x_SLEEP.C: 88: unsigned char a,b;
		//;test_61f14x_SLEEP.C: 89: for(a=0;a<Time;a++)
		CLRF 	73H 			//07C5 	11F3
		LDR 	72H, 0H 			//07C6 	1872
		SUBWR 	73H, 0H 		//07C7 	1273
		BTSC 	3H, 0H 			//07C8 	2803
		RET 					//07C9 	1008

		//;test_61f14x_SLEEP.C: 90: {
		//;test_61f14x_SLEEP.C: 91: for(b=0;b<5;b++)
		CLRF 	74H 			//07CA 	11F4
		ORG		07CBH

		//;test_61f14x_SLEEP.C: 92: {
		//;test_61f14x_SLEEP.C: 93: DelayUs(197);
		LDWI 	C5H 			//07CB 	00C5
		LCALL 	7D5H 			//07CC 	37D5
		MOVLP 	7H 			//07CD 	0187
		LDWI 	5H 			//07CE 	0005
		INCR 	74H, 1H 		//07CF 	1AF4
		SUBWR 	74H, 0H 		//07D0 	1274
		BTSS 	3H, 0H 			//07D1 	2C03
		LJUMP 	7CBH 			//07D2 	3FCB
		ORG		07D3H
		INCR 	73H, 1H 		//07D3 	1AF3
		LJUMP 	7C6H 			//07D4 	3FC6
		STR 	70H 			//07D5 	10F0

		//;test_61f14x_SLEEP.C: 74: unsigned char a;
		//;test_61f14x_SLEEP.C: 75: for(a=0;a<Time;a++)
		CLRF 	71H 			//07D6 	11F1
		LDR 	70H, 0H 			//07D7 	1870
		SUBWR 	71H, 0H 		//07D8 	1271
		BTSC 	3H, 0H 			//07D9 	2803
		RET 					//07DA 	1008
		ORG		07DBH

		//;test_61f14x_SLEEP.C: 76: {
		//;test_61f14x_SLEEP.C: 77: __nop();
		NOP 					//07DB 	1000
		INCR 	71H, 1H 		//07DC 	1AF1
		LJUMP 	7D7H 			//07DD 	3FD7

		//;test_61f14x_SLEEP.C: 39: OSCCON = 0B01110001;
		LDWI 	71H 			//07DE 	0071
		MOVLB 	1H 			//07DF 	1021
		STR 	19H 			//07E0 	1099

		//;test_61f14x_SLEEP.C: 40: INTCON = 0;
		CLRF 	BH 			//07E1 	118B

		//;test_61f14x_SLEEP.C: 42: PORTA = 0B00000000;
		MOVLB 	0H 			//07E2 	1020
		ORG		07E3H
		CLRF 	CH 			//07E3 	118C

		//;test_61f14x_SLEEP.C: 43: TRISA = 0B00000000;
		MOVLB 	1H 			//07E4 	1021
		CLRF 	CH 			//07E5 	118C

		//;test_61f14x_SLEEP.C: 44: PORTB = 0B00000000;
		MOVLB 	0H 			//07E6 	1020
		CLRF 	DH 			//07E7 	118D

		//;test_61f14x_SLEEP.C: 45: TRISB = 0B00000000;
		MOVLB 	1H 			//07E8 	1021
		CLRF 	DH 			//07E9 	118D

		//;test_61f14x_SLEEP.C: 46: PORTC = 0B00000000;
		MOVLB 	0H 			//07EA 	1020
		ORG		07EBH
		CLRF 	EH 			//07EB 	118E

		//;test_61f14x_SLEEP.C: 47: TRISC = 0B00000000;
		MOVLB 	1H 			//07EC 	1021
		CLRF 	EH 			//07ED 	118E

		//;test_61f14x_SLEEP.C: 49: WPUA = 0B00000000;
		MOVLB 	3H 			//07EE 	1023
		CLRF 	CH 			//07EF 	118C

		//;test_61f14x_SLEEP.C: 50: WPUB = 0B00000000;
		CLRF 	DH 			//07F0 	118D

		//;test_61f14x_SLEEP.C: 51: WPUC = 0B00000000;
		CLRF 	EH 			//07F1 	118E

		//;test_61f14x_SLEEP.C: 53: WPDA = 0B00000000;
		MOVLB 	4H 			//07F2 	1024
		ORG		07F3H
		CLRF 	CH 			//07F3 	118C

		//;test_61f14x_SLEEP.C: 54: WPDB = 0B00000000;
		CLRF 	DH 			//07F4 	118D

		//;test_61f14x_SLEEP.C: 55: WPDC = 0B00000000;
		CLRF 	EH 			//07F5 	118E

		//;test_61f14x_SLEEP.C: 57: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07F6 	00FF
		MOVLB 	2H 			//07F7 	1022
		STR 	1AH 			//07F8 	109A

		//;test_61f14x_SLEEP.C: 58: PSRC1 = 0B11111111;
		STR 	1BH 			//07F9 	109B

		//;test_61f14x_SLEEP.C: 60: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07FA 	1023
		ORG		07FBH
		STR 	1AH 			//07FB 	109A

		//;test_61f14x_SLEEP.C: 61: PSINK1 = 0B11111111;
		STR 	1BH 			//07FC 	109B

		//;test_61f14x_SLEEP.C: 62: PSINK2 = 0B11111111;
		STR 	1CH 			//07FD 	109C

		//;test_61f14x_SLEEP.C: 64: ANSELA = 0B00000000;
		CLRF 	17H 			//07FE 	1197
		RET 					//07FF 	1008
			END
