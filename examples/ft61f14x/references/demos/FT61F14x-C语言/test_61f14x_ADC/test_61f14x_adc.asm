//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_adcData		EQU		7CH
		_theVoltage		EQU		24H
//		___lmul@product		EQU		78H
//		___lmul@multiplier		EQU		70H
//		___lmul@multiplicand		EQU		74H
//		GET_ADC_DATA@adcChannel		EQU		75H
//		GET_ADC_DATA@adcChannel		EQU		C00000H
//		DelayUs@Time		EQU		70H
//		DelayUs@a		EQU		71H
//		DelayUs@Time		EQU		C00000H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2H 			//0001 	3802
		MOVLP 	7H 			//0002 	0187
		LJUMP 	752H 			//0003 	3F52
		ORG		0752H
		MOVLB 	0H 			//0752 	1020
		LJUMP 	754H 			//0753 	3F54

		//;test_61f14x_ADC.C: 249: POWER_INITIAL();
		LCALL 	7B9H 			//0754 	37B9
		MOVLP 	7H 			//0755 	0187

		//;test_61f14x_ADC.C: 250: ADC_INITIAL();
		LCALL 	788H 			//0756 	3788
		MOVLP 	7H 			//0757 	0187

		//;test_61f14x_ADC.C: 252: while(1)
		//;test_61f14x_ADC.C: 253: {
		//;test_61f14x_ADC.C: 254: adcData = GET_ADC_DATA(0);
		LDWI 	0H 			//0758 	0000
		LCALL 	799H 			//0759 	3799
		ORG		075AH
		MOVLP 	7H 			//075A 	0187
		LDR 	73H, 0H 			//075B 	1873
		STR 	7DH 			//075C 	10FD
		LDR 	72H, 0H 			//075D 	1872
		STR 	7CH 			//075E 	10FC

		//;test_61f14x_ADC.C: 255: theVoltage = (unsigned long)adcData*2*1000/4096;
		LDR 	7CH, 0H 			//075F 	187C
		STR 	70H 			//0760 	10F0
		LDR 	7DH, 0H 			//0761 	187D
		ORG		0762H
		STR 	71H 			//0762 	10F1
		LDWI 	3H 			//0763 	0003
		CLRF 	72H 			//0764 	11F2
		CLRF 	73H 			//0765 	11F3
		LSLF 	70H, 1H 		//0766 	05F0
		RLR 	71H, 1H 			//0767 	1DF1
		RLR 	72H, 1H 			//0768 	1DF2
		RLR 	73H, 1H 			//0769 	1DF3
		ORG		076AH
		CLRF 	77H 			//076A 	11F7
		CLRF 	76H 			//076B 	11F6
		STR 	75H 			//076C 	10F5
		LDWI 	E8H 			//076D 	00E8
		STR 	74H 			//076E 	10F4
		LCALL 	7DBH 			//076F 	37DB
		MOVLP 	7H 			//0770 	0187
		LDR 	70H, 0H 			//0771 	1870
		ORG		0772H
		MOVLB 	0H 			//0772 	1020
		STR 	20H 			//0773 	10A0
		LDR 	71H, 0H 			//0774 	1871
		STR 	21H 			//0775 	10A1
		LDR 	72H, 0H 			//0776 	1872
		STR 	22H 			//0777 	10A2
		LDR 	73H, 0H 			//0778 	1873
		STR 	23H 			//0779 	10A3
		ORG		077AH
		LDWI 	CH 			//077A 	000C
		LSRF 	23H, 1H 		//077B 	06A3
		RRR 	22H, 1H 			//077C 	1CA2
		RRR 	21H, 1H 			//077D 	1CA1
		RRR 	20H, 1H 			//077E 	1CA0
		DECRSZ 	9H, 1H 		//077F 	1B89
		LJUMP 	77BH 			//0780 	3F7B
		LDR 	21H, 0H 			//0781 	1821
		ORG		0782H
		STR 	25H 			//0782 	10A5
		LDR 	20H, 0H 			//0783 	1820
		STR 	24H 			//0784 	10A4

		//;test_61f14x_ADC.C: 256: __nop();
		NOP 					//0785 	1000

		//;test_61f14x_ADC.C: 257: __nop();
		NOP 					//0786 	1000
		LJUMP 	758H 			//0787 	3F58

		//;test_61f14x_ADC.C: 100: ANSELA = 0B00000001;
		LDWI 	1H 			//0788 	0001
		STR 	17H 			//0789 	1097
		ORG		078AH

		//;test_61f14x_ADC.C: 102: ADCON1 = 0B11100100;
		LDWI 	E4H 			//078A 	00E4
		MOVLB 	1H 			//078B 	1021
		STR 	1EH 			//078C 	109E

		//;test_61f14x_ADC.C: 129: ADCON0 = 0B00000000;
		CLRF 	1DH 			//078D 	119D

		//;test_61f14x_ADC.C: 158: ADCON2 = 0B01000000;
		LDWI 	40H 			//078E 	0040
		STR 	1FH 			//078F 	109F

		//;test_61f14x_ADC.C: 186: ADCON3 = 0B00000000;
		MOVLB 	8H 			//0790 	1028
		CLRF 	1AH 			//0791 	119A
		ORG		0792H

		//;test_61f14x_ADC.C: 213: ADDLY = 0B00000000;
		MOVLB 	0H 			//0792 	1020
		CLRF 	1FH 			//0793 	119F

		//;test_61f14x_ADC.C: 218: ADCMPH = 0B00000000;
		MOVLB 	8H 			//0794 	1028
		CLRF 	1BH 			//0795 	119B

		//;test_61f14x_ADC.C: 221: ADON=1;
		MOVLB 	1H 			//0796 	1021
		BSR 	1DH, 0H 			//0797 	241D
		RET 					//0798 	1008
		STR 	75H 			//0799 	10F5
		ORG		079AH

		//;test_61f14x_ADC.C: 231: ADCON0 &= 0B00001111;
		LDWI 	FH 			//079A 	000F
		MOVLB 	1H 			//079B 	1021
		ANDWR 	1DH, 1H 		//079C 	159D

		//;test_61f14x_ADC.C: 232: ADCON0 |= adcChannel<<4;
		SWAPR 	75H, 0H 		//079D 	1E75
		ANDWI 	F0H 			//079E 	09F0
		IORWR 	1DH, 1H 		//079F 	149D

		//;test_61f14x_ADC.C: 233: DelayUs(40);
		LDWI 	28H 			//07A0 	0028
		LCALL 	7B0H 			//07A1 	37B0
		ORG		07A2H
		MOVLP 	7H 			//07A2 	0187

		//;test_61f14x_ADC.C: 234: GO = 1;
		MOVLB 	1H 			//07A3 	1021
		BSR 	1DH, 1H 			//07A4 	249D

		//;test_61f14x_ADC.C: 235: __nop();
		NOP 					//07A5 	1000

		//;test_61f14x_ADC.C: 236: __nop();
		NOP 					//07A6 	1000

		//;test_61f14x_ADC.C: 237: while(GO);
		MOVLB 	1H 			//07A7 	1021
		BTSC 	1DH, 1H 		//07A8 	289D
		LJUMP 	7A7H 			//07A9 	3FA7
		ORG		07AAH

		//;test_61f14x_ADC.C: 239: return (unsigned int)(ADRESH<<8|ADRESL);
		LDR 	1CH, 0H 			//07AA 	181C
		STR 	73H 			//07AB 	10F3
		CLRF 	72H 			//07AC 	11F2
		LDR 	1BH, 0H 			//07AD 	181B
		IORWR 	72H, 1H 		//07AE 	14F2
		RET 					//07AF 	1008
		STR 	70H 			//07B0 	10F0

		//;test_61f14x_ADC.C: 86: unsigned char a;
		//;test_61f14x_ADC.C: 87: for(a=0;a<Time;a++)
		CLRF 	71H 			//07B1 	11F1
		ORG		07B2H
		LDR 	70H, 0H 			//07B2 	1870
		SUBWR 	71H, 0H 		//07B3 	1271
		BTSC 	3H, 0H 			//07B4 	2803
		RET 					//07B5 	1008

		//;test_61f14x_ADC.C: 88: {
		//;test_61f14x_ADC.C: 89: __nop();
		NOP 					//07B6 	1000
		INCR 	71H, 1H 		//07B7 	1AF1
		LJUMP 	7B2H 			//07B8 	3FB2

		//;test_61f14x_ADC.C: 39: OSCCON = 0B01110001;
		LDWI 	71H 			//07B9 	0071
		ORG		07BAH
		MOVLB 	1H 			//07BA 	1021
		STR 	19H 			//07BB 	1099

		//;test_61f14x_ADC.C: 46: PCKEN |=0B00000001;
		BSR 	1AH, 0H 			//07BC 	241A

		//;test_61f14x_ADC.C: 48: INTCON = 0;
		CLRF 	BH 			//07BD 	118B

		//;test_61f14x_ADC.C: 50: PORTA = 0B00000000;
		MOVLB 	0H 			//07BE 	1020
		CLRF 	CH 			//07BF 	118C

		//;test_61f14x_ADC.C: 51: TRISA = 0B11111111;
		LDWI 	FFH 			//07C0 	00FF
		MOVLB 	1H 			//07C1 	1021
		ORG		07C2H
		STR 	CH 			//07C2 	108C

		//;test_61f14x_ADC.C: 52: PORTB = 0B00000000;
		MOVLB 	0H 			//07C3 	1020
		CLRF 	DH 			//07C4 	118D

		//;test_61f14x_ADC.C: 53: TRISB = 0B11111111;
		MOVLB 	1H 			//07C5 	1021
		STR 	DH 			//07C6 	108D

		//;test_61f14x_ADC.C: 54: PORTC = 0B00000000;
		MOVLB 	0H 			//07C7 	1020
		CLRF 	EH 			//07C8 	118E

		//;test_61f14x_ADC.C: 55: TRISC = 0B11111111;
		MOVLB 	1H 			//07C9 	1021
		ORG		07CAH
		STR 	EH 			//07CA 	108E

		//;test_61f14x_ADC.C: 57: WPUA = 0B00000000;
		MOVLB 	3H 			//07CB 	1023
		CLRF 	CH 			//07CC 	118C

		//;test_61f14x_ADC.C: 58: WPUB = 0B00000000;
		CLRF 	DH 			//07CD 	118D

		//;test_61f14x_ADC.C: 59: WPUC = 0B00000000;
		CLRF 	EH 			//07CE 	118E

		//;test_61f14x_ADC.C: 61: WPDA = 0B00000000;
		MOVLB 	4H 			//07CF 	1024
		CLRF 	CH 			//07D0 	118C

		//;test_61f14x_ADC.C: 62: WPDB = 0B00000000;
		CLRF 	DH 			//07D1 	118D
		ORG		07D2H

		//;test_61f14x_ADC.C: 63: WPDC = 0B00000000;
		CLRF 	EH 			//07D2 	118E

		//;test_61f14x_ADC.C: 65: PSRC0 = 0B11111111;
		MOVLB 	2H 			//07D3 	1022
		STR 	1AH 			//07D4 	109A

		//;test_61f14x_ADC.C: 69: PSRC1 = 0B11111111;
		STR 	1BH 			//07D5 	109B

		//;test_61f14x_ADC.C: 73: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07D6 	1023
		STR 	1AH 			//07D7 	109A

		//;test_61f14x_ADC.C: 74: PSINK1 = 0B11111111;
		STR 	1BH 			//07D8 	109B

		//;test_61f14x_ADC.C: 75: PSINK2 = 0B11111111;
		STR 	1CH 			//07D9 	109C
		ORG		07DAH
		RET 					//07DA 	1008
		CLRF 	78H 			//07DB 	11F8
		CLRF 	79H 			//07DC 	11F9
		CLRF 	7AH 			//07DD 	11FA
		CLRF 	7BH 			//07DE 	11FB
		BTSS 	70H, 0H 		//07DF 	2C70
		LJUMP 	7E9H 			//07E0 	3FE9
		LDR 	74H, 0H 			//07E1 	1874
		ORG		07E2H
		ADDWR 	78H, 1H 		//07E2 	17F8
		LDR 	75H, 0H 			//07E3 	1875
		ADDWFC 	79H, 1H 		//07E4 	0DF9
		LDR 	76H, 0H 			//07E5 	1876
		ADDWFC 	7AH, 1H 		//07E6 	0DFA
		LDR 	77H, 0H 			//07E7 	1877
		ADDWFC 	7BH, 1H 		//07E8 	0DFB
		LSLF 	74H, 1H 		//07E9 	05F4
		ORG		07EAH
		RLR 	75H, 1H 			//07EA 	1DF5
		RLR 	76H, 1H 			//07EB 	1DF6
		RLR 	77H, 1H 			//07EC 	1DF7
		LSRF 	73H, 1H 		//07ED 	06F3
		RRR 	72H, 1H 			//07EE 	1CF2
		RRR 	71H, 1H 			//07EF 	1CF1
		RRR 	70H, 1H 			//07F0 	1CF0
		LDR 	73H, 0H 			//07F1 	1873
		ORG		07F2H
		IORWR 	72H, 0H 		//07F2 	1472
		IORWR 	71H, 0H 		//07F3 	1471
		IORWR 	70H, 0H 		//07F4 	1470
		BTSS 	3H, 2H 			//07F5 	2D03
		LJUMP 	7DFH 			//07F6 	3FDF
		LDR 	7BH, 0H 			//07F7 	187B
		STR 	73H 			//07F8 	10F3
		LDR 	7AH, 0H 			//07F9 	187A
		ORG		07FAH
		STR 	72H 			//07FA 	10F2
		LDR 	79H, 0H 			//07FB 	1879
		STR 	71H 			//07FC 	10F1
		LDR 	78H, 0H 			//07FD 	1878
		STR 	70H 			//07FE 	10F0
		RET 					//07FF 	1008
			END
