//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_TestBuff		EQU		75H
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
		LJUMP 	79EH 			//0003 	3F9E
		ORG		079EH
		MOVLB 	0H 			//079E 	1020
		LJUMP 	7A0H 			//079F 	3FA0

		//;test_61f14x_MSCK.C: 125: POWER_INITIAL();
		LCALL 	7C9H 			//07A0 	37C9
		MOVLP 	7H 			//07A1 	0187

		//;test_61f14x_MSCK.C: 127: {
		//;test_61f14x_MSCK.C: 128: TestBuff = SlowTimeTest();
		LCALL 	7EBH 			//07A2 	37EB
		MOVLP 	7H 			//07A3 	0187
		LDR 	71H, 0H 			//07A4 	1871
		STR 	76H 			//07A5 	10F6
		ORG		07A6H
		LDR 	70H, 0H 			//07A6 	1870
		STR 	75H 			//07A7 	10F5

		//;test_61f14x_MSCK.C: 130: __nop();
		NOP 					//07A8 	1000

		//;test_61f14x_MSCK.C: 131: __nop();
		NOP 					//07A9 	1000

		//;test_61f14x_MSCK.C: 132: __nop();
		NOP 					//07AA 	1000

		//;test_61f14x_MSCK.C: 133: DelayMs(200);
		LDWI 	C8H 			//07AB 	00C8
		LCALL 	7AFH 			//07AC 	37AF
		MOVLP 	7H 			//07AD 	0187
		ORG		07AEH
		LJUMP 	7A2H 			//07AE 	3FA2
		STR 	72H 			//07AF 	10F2

		//;test_61f14x_MSCK.C: 86: unsigned char a,b;
		//;test_61f14x_MSCK.C: 87: for(a=0;a<Time;a++)
		CLRF 	73H 			//07B0 	11F3
		LDR 	72H, 0H 			//07B1 	1872
		SUBWR 	73H, 0H 		//07B2 	1273
		BTSC 	3H, 0H 			//07B3 	2803
		RET 					//07B4 	1008

		//;test_61f14x_MSCK.C: 88: {
		//;test_61f14x_MSCK.C: 89: for(b=0;b<5;b++)
		CLRF 	74H 			//07B5 	11F4
		ORG		07B6H

		//;test_61f14x_MSCK.C: 90: {
		//;test_61f14x_MSCK.C: 91: DelayUs(197);
		LDWI 	C5H 			//07B6 	00C5
		LCALL 	7C0H 			//07B7 	37C0
		MOVLP 	7H 			//07B8 	0187
		LDWI 	5H 			//07B9 	0005
		INCR 	74H, 1H 		//07BA 	1AF4
		SUBWR 	74H, 0H 		//07BB 	1274
		BTSS 	3H, 0H 			//07BC 	2C03
		LJUMP 	7B6H 			//07BD 	3FB6
		ORG		07BEH
		INCR 	73H, 1H 		//07BE 	1AF3
		LJUMP 	7B1H 			//07BF 	3FB1
		STR 	70H 			//07C0 	10F0

		//;test_61f14x_MSCK.C: 72: unsigned char a;
		//;test_61f14x_MSCK.C: 73: for(a=0;a<Time;a++)
		CLRF 	71H 			//07C1 	11F1
		LDR 	70H, 0H 			//07C2 	1870
		SUBWR 	71H, 0H 		//07C3 	1271
		BTSC 	3H, 0H 			//07C4 	2803
		RET 					//07C5 	1008
		ORG		07C6H

		//;test_61f14x_MSCK.C: 74: {
		//;test_61f14x_MSCK.C: 75: __nop();
		NOP 					//07C6 	1000
		INCR 	71H, 1H 		//07C7 	1AF1
		LJUMP 	7C2H 			//07C8 	3FC2

		//;test_61f14x_MSCK.C: 37: OSCCON = 0B01110001;
		LDWI 	71H 			//07C9 	0071
		MOVLB 	1H 			//07CA 	1021
		STR 	19H 			//07CB 	1099

		//;test_61f14x_MSCK.C: 38: INTCON = 0;
		CLRF 	BH 			//07CC 	118B

		//;test_61f14x_MSCK.C: 40: PORTA = 0B00000000;
		MOVLB 	0H 			//07CD 	1020
		ORG		07CEH
		CLRF 	CH 			//07CE 	118C

		//;test_61f14x_MSCK.C: 41: TRISA = 0B00000000;
		MOVLB 	1H 			//07CF 	1021
		CLRF 	CH 			//07D0 	118C

		//;test_61f14x_MSCK.C: 42: PORTB = 0B00000000;
		MOVLB 	0H 			//07D1 	1020
		CLRF 	DH 			//07D2 	118D

		//;test_61f14x_MSCK.C: 43: TRISB = 0B00000000;
		MOVLB 	1H 			//07D3 	1021
		CLRF 	DH 			//07D4 	118D

		//;test_61f14x_MSCK.C: 44: PORTC = 0B00000000;
		MOVLB 	0H 			//07D5 	1020
		ORG		07D6H
		CLRF 	EH 			//07D6 	118E

		//;test_61f14x_MSCK.C: 45: TRISC = 0B00000000;
		MOVLB 	1H 			//07D7 	1021
		CLRF 	EH 			//07D8 	118E

		//;test_61f14x_MSCK.C: 47: WPUA = 0B00000000;
		MOVLB 	3H 			//07D9 	1023
		CLRF 	CH 			//07DA 	118C

		//;test_61f14x_MSCK.C: 48: WPUB = 0B00000000;
		CLRF 	DH 			//07DB 	118D

		//;test_61f14x_MSCK.C: 49: WPUC = 0B00000000;
		CLRF 	EH 			//07DC 	118E

		//;test_61f14x_MSCK.C: 51: WPDA = 0B00000000;
		MOVLB 	4H 			//07DD 	1024
		ORG		07DEH
		CLRF 	CH 			//07DE 	118C

		//;test_61f14x_MSCK.C: 52: WPDB = 0B00000000;
		CLRF 	DH 			//07DF 	118D

		//;test_61f14x_MSCK.C: 53: WPDC = 0B00000000;
		CLRF 	EH 			//07E0 	118E

		//;test_61f14x_MSCK.C: 55: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07E1 	00FF
		MOVLB 	2H 			//07E2 	1022
		STR 	1AH 			//07E3 	109A

		//;test_61f14x_MSCK.C: 56: PSRC1 = 0B11111111;
		STR 	1BH 			//07E4 	109B

		//;test_61f14x_MSCK.C: 58: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07E5 	1023
		ORG		07E6H
		STR 	1AH 			//07E6 	109A

		//;test_61f14x_MSCK.C: 59: PSINK1 = 0B11111111;
		STR 	1BH 			//07E7 	109B

		//;test_61f14x_MSCK.C: 60: PSINK2 = 0B11111111;
		STR 	1CH 			//07E8 	109C

		//;test_61f14x_MSCK.C: 62: ANSELA = 0B00000000;
		CLRF 	17H 			//07E9 	1197
		RET 					//07EA 	1008

		//;test_61f14x_MSCK.C: 105: PCKEN |= 0B00000100;
		MOVLB 	1H 			//07EB 	1021
		BSR 	1AH, 2H 			//07EC 	251A

		//;test_61f14x_MSCK.C: 106: TCKSRC= 0B00010000;
		LDWI 	10H 			//07ED 	0010
		ORG		07EEH
		MOVLB 	6H 			//07EE 	1026
		STR 	1FH 			//07EF 	109F

		//;test_61f14x_MSCK.C: 107: T2CEN = 1;
		BSR 	CH, 0H 			//07F0 	240C

		//;test_61f14x_MSCK.C: 108: CKMAVG = 0;
		MOVLB 	8H 			//07F1 	1028
		BCR 	1DH, 1H 			//07F2 	209D

		//;test_61f14x_MSCK.C: 110: CKCNTI = 1;
		BSR 	1DH, 0H 			//07F3 	241D

		//;test_61f14x_MSCK.C: 111: __nop();
		NOP 					//07F4 	1000

		//;test_61f14x_MSCK.C: 112: while(!CKMIF);
		MOVLB 	0H 			//07F5 	1020
		ORG		07F6H
		BTSS 	11H, 1H 		//07F6 	2C91
		LJUMP 	7F5H 			//07F7 	3FF5

		//;test_61f14x_MSCK.C: 113: CKMIF=0;
		BCR 	11H, 1H 			//07F8 	2091

		//;test_61f14x_MSCK.C: 114: return (unsigned int)(SOSCPRH<<8|SOSCPRL);
		MOVLB 	8H 			//07F9 	1028
		LDR 	1FH, 0H 			//07FA 	181F
		STR 	71H 			//07FB 	10F1
		CLRF 	70H 			//07FC 	11F0
		LDR 	1EH, 0H 			//07FD 	181E
		ORG		07FEH
		IORWR 	70H, 1H 		//07FE 	14F0
		RET 					//07FF 	1008
			END
