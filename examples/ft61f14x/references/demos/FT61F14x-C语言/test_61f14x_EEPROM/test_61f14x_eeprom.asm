//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_EEReadData		EQU		72H
//		EEPROMwrite@EEAddr		EQU		71H
//		EEPROMwrite@Data		EQU		70H
//		EEPROMwrite@EEAddr		EQU		C00000H
//		EEPROMread@EEAddr		EQU		70H
//		EEPROMread@ReEEPROMread		EQU		71H
//		EEPROMread@EEAddr		EQU		C00000H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2H 			//0001 	3802
		MOVLP 	7H 			//0002 	0187
		LJUMP 	791H 			//0003 	3F91
		ORG		0791H
		CLRF 	72H 			//0791 	11F2
		MOVLB 	0H 			//0792 	1020
		LJUMP 	794H 			//0793 	3F94

		//;test_61f14x_EEPROM.C: 153: POWER_INITIAL();
		LCALL 	7DDH 			//0794 	37DD
		MOVLP 	7H 			//0795 	0187

		//;test_61f14x_EEPROM.C: 155: EEPROMwrite(0x13,0x55);
		LDWI 	55H 			//0796 	0055
		STR 	70H 			//0797 	10F0
		LDWI 	13H 			//0798 	0013
		ORG		0799H
		LCALL 	7B7H 			//0799 	37B7
		MOVLP 	7H 			//079A 	0187

		//;test_61f14x_EEPROM.C: 157: EEReadData = EEPROMread(0x13);
		LDWI 	13H 			//079B 	0013
		LCALL 	7A2H 			//079C 	37A2
		MOVLP 	7H 			//079D 	0187
		STR 	72H 			//079E 	10F2

		//;test_61f14x_EEPROM.C: 160: {
		//;test_61f14x_EEPROM.C: 161: __nop();
		NOP 					//079F 	1000

		//;test_61f14x_EEPROM.C: 162: __nop();
		NOP 					//07A0 	1000
		ORG		07A1H
		LJUMP 	79FH 			//07A1 	3F9F
		STR 	70H 			//07A2 	10F0

		//;test_61f14x_EEPROM.C: 72: unsigned char ReEEPROMread;
		//;test_61f14x_EEPROM.C: 73: while(GIE)
		BTSS 	BH, 7H 			//07A3 	2F8B
		LJUMP 	7A9H 			//07A4 	3FA9

		//;test_61f14x_EEPROM.C: 74: {
		//;test_61f14x_EEPROM.C: 75: GIE = 0;
		BCR 	BH, 7H 			//07A5 	238B

		//;test_61f14x_EEPROM.C: 76: __nop();
		NOP 					//07A6 	1000

		//;test_61f14x_EEPROM.C: 77: __nop();
		NOP 					//07A7 	1000
		LJUMP 	7A3H 			//07A8 	3FA3
		ORG		07A9H

		//;test_61f14x_EEPROM.C: 78: }
		//;test_61f14x_EEPROM.C: 79: EEADRL = EEAddr;
		LDR 	70H, 0H 			//07A9 	1870
		MOVLB 	3H 			//07AA 	1023
		STR 	11H 			//07AB 	1091

		//;test_61f14x_EEPROM.C: 81: CFGS =0;
		BCR 	15H, 6H 			//07AC 	2315

		//;test_61f14x_EEPROM.C: 82: EEPGD=0;
		BCR 	15H, 7H 			//07AD 	2395

		//;test_61f14x_EEPROM.C: 83: RD = 1;
		BSR 	15H, 0H 			//07AE 	2415

		//;test_61f14x_EEPROM.C: 84: __nop();
		NOP 					//07AF 	1000

		//;test_61f14x_EEPROM.C: 85: __nop();
		NOP 					//07B0 	1000
		ORG		07B1H

		//;test_61f14x_EEPROM.C: 86: __nop();
		NOP 					//07B1 	1000

		//;test_61f14x_EEPROM.C: 87: __nop();
		NOP 					//07B2 	1000

		//;test_61f14x_EEPROM.C: 88: ReEEPROMread = EEDATL;
		MOVLB 	3H 			//07B3 	1023
		LDR 	13H, 0H 			//07B4 	1813
		STR 	71H 			//07B5 	10F1

		//;test_61f14x_EEPROM.C: 89: return ReEEPROMread;
		RET 					//07B6 	1008
		STR 	71H 			//07B7 	10F1

		//;test_61f14x_EEPROM.C: 121: while(GIE)
		BTSS 	BH, 7H 			//07B8 	2F8B
		ORG		07B9H
		LJUMP 	7BEH 			//07B9 	3FBE

		//;test_61f14x_EEPROM.C: 122: {
		//;test_61f14x_EEPROM.C: 123: GIE = 0;
		BCR 	BH, 7H 			//07BA 	238B

		//;test_61f14x_EEPROM.C: 124: __nop();
		NOP 					//07BB 	1000

		//;test_61f14x_EEPROM.C: 125: __nop();
		NOP 					//07BC 	1000
		LJUMP 	7B8H 			//07BD 	3FB8

		//;test_61f14x_EEPROM.C: 126: }
		//;test_61f14x_EEPROM.C: 127: EEADRL = EEAddr;
		LDR 	71H, 0H 			//07BE 	1871
		MOVLB 	3H 			//07BF 	1023
		STR 	11H 			//07C0 	1091
		ORG		07C1H

		//;test_61f14x_EEPROM.C: 128: EEDATL = Data;
		LDR 	70H, 0H 			//07C1 	1870
		STR 	13H 			//07C2 	1093

		//;test_61f14x_EEPROM.C: 130: CFGS =0;
		BCR 	15H, 6H 			//07C3 	2315

		//;test_61f14x_EEPROM.C: 131: EEPGD=0;
		BCR 	15H, 7H 			//07C4 	2395

		//;test_61f14x_EEPROM.C: 132: EEIF = 0;
		BCR 	BH, 2H 			//07C5 	210B

		//;test_61f14x_EEPROM.C: 133: WREN=1;
		BSR 	15H, 2H 			//07C6 	2515

		//;test_61f14x_EEPROM.C: 135: Unlock_Flash();
		LCALL 	7D3H 			//07C7 	37D3
		MOVLP 	7H 			//07C8 	0187
		ORG		07C9H

		//;test_61f14x_EEPROM.C: 136: __nop();
		NOP 					//07C9 	1000

		//;test_61f14x_EEPROM.C: 137: __nop();
		NOP 					//07CA 	1000

		//;test_61f14x_EEPROM.C: 138: __nop();
		NOP 					//07CB 	1000

		//;test_61f14x_EEPROM.C: 139: __nop();
		NOP 					//07CC 	1000

		//;test_61f14x_EEPROM.C: 141: while(WR);
		MOVLB 	3H 			//07CD 	1023
		BTSC 	15H, 1H 		//07CE 	2895
		LJUMP 	7CDH 			//07CF 	3FCD

		//;test_61f14x_EEPROM.C: 142: WREN=0;
		BCR 	15H, 2H 			//07D0 	2115
		ORG		07D1H

		//;test_61f14x_EEPROM.C: 143: GIE = 1;
		BSR 	BH, 7H 			//07D1 	278B
		RET 					//07D2 	1008
		LDWI 	3H 			//07D3 	0003
		STR 	8H 			//07D4 	1088
		LDWI 	55H 			//07D5 	0055
		STR 	16H 			//07D6 	1096
		LDWI 	AAH 			//07D7 	00AA
		STR 	16H 			//07D8 	1096
		ORG		07D9H
		BSR 	15H, 1H 			//07D9 	2495
		NOP 					//07DA 	1000
		NOP 					//07DB 	1000
		RET 					//07DC 	1008

		//;test_61f14x_EEPROM.C: 37: OSCCON = 0B01110001;
		LDWI 	71H 			//07DD 	0071
		MOVLB 	1H 			//07DE 	1021
		STR 	19H 			//07DF 	1099

		//;test_61f14x_EEPROM.C: 38: INTCON = 0;
		CLRF 	BH 			//07E0 	118B
		ORG		07E1H

		//;test_61f14x_EEPROM.C: 40: PORTA = 0B00000000;
		MOVLB 	0H 			//07E1 	1020
		CLRF 	CH 			//07E2 	118C

		//;test_61f14x_EEPROM.C: 41: TRISA = 0B00000000;
		MOVLB 	1H 			//07E3 	1021
		CLRF 	CH 			//07E4 	118C

		//;test_61f14x_EEPROM.C: 42: PORTB = 0B00000000;
		MOVLB 	0H 			//07E5 	1020
		CLRF 	DH 			//07E6 	118D

		//;test_61f14x_EEPROM.C: 43: TRISB = 0B00000000;
		MOVLB 	1H 			//07E7 	1021
		CLRF 	DH 			//07E8 	118D
		ORG		07E9H

		//;test_61f14x_EEPROM.C: 44: PORTC = 0B00000000;
		MOVLB 	0H 			//07E9 	1020
		CLRF 	EH 			//07EA 	118E

		//;test_61f14x_EEPROM.C: 45: TRISC = 0B00000000;
		MOVLB 	1H 			//07EB 	1021
		CLRF 	EH 			//07EC 	118E

		//;test_61f14x_EEPROM.C: 47: WPUA = 0B00000000;
		MOVLB 	3H 			//07ED 	1023
		CLRF 	CH 			//07EE 	118C

		//;test_61f14x_EEPROM.C: 48: WPUB = 0B00000000;
		CLRF 	DH 			//07EF 	118D

		//;test_61f14x_EEPROM.C: 49: WPUC = 0B00001000;
		LDWI 	8H 			//07F0 	0008
		ORG		07F1H
		STR 	EH 			//07F1 	108E

		//;test_61f14x_EEPROM.C: 51: WPDA = 0B00000000;
		MOVLB 	4H 			//07F2 	1024
		CLRF 	CH 			//07F3 	118C

		//;test_61f14x_EEPROM.C: 52: WPDB = 0B00000000;
		CLRF 	DH 			//07F4 	118D

		//;test_61f14x_EEPROM.C: 53: WPDC = 0B00000000;
		CLRF 	EH 			//07F5 	118E

		//;test_61f14x_EEPROM.C: 55: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07F6 	00FF
		MOVLB 	2H 			//07F7 	1022
		STR 	1AH 			//07F8 	109A
		ORG		07F9H

		//;test_61f14x_EEPROM.C: 56: PSRC1 = 0B11111111;
		STR 	1BH 			//07F9 	109B

		//;test_61f14x_EEPROM.C: 58: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07FA 	1023
		STR 	1AH 			//07FB 	109A

		//;test_61f14x_EEPROM.C: 59: PSINK1 = 0B11111111;
		STR 	1BH 			//07FC 	109B

		//;test_61f14x_EEPROM.C: 60: PSINK2 = 0B11111111;
		STR 	1CH 			//07FD 	109C

		//;test_61f14x_EEPROM.C: 62: ANSELA = 0B00000000;
		CLRF 	17H 			//07FE 	1197
		RET 					//07FF 	1008
			END
