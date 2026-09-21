//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_SPIReadData		EQU		76H
//		SPI_Write@addr		EQU		73H
//		SPI_Write@dat		EQU		75H
//		SPI_Read@spidata		EQU		75H
//		SPI_Read@addr		EQU		73H
//		SPI_ReadStatus@status		EQU		72H
//		SPI_RW@data		EQU		71H
//		SPI_RW@i		EQU		70H
//		SPI_RW@data		EQU		C00000H
//-----------------------Variable END---------------------------------
		ORG		0000H
		MOVLP 	0H 			//0000 	0180
		LJUMP 	2H 			//0001 	3802
		MOVLP 	7H 			//0002 	0187
		LJUMP 	762H 			//0003 	3F62
		ORG		0762H
		MOVLB 	0H 			//0762 	1020
		LJUMP 	764H 			//0763 	3F64

		//;test_61f14x_SPI.C: 203: SPIReadData=0;
		CLRF 	76H 			//0764 	11F6

		//;test_61f14x_SPI.C: 204: POWER_INITIAL();
		LCALL 	7CEH 			//0765 	37CE
		MOVLP 	7H 			//0766 	0187

		//;test_61f14x_SPI.C: 205: init_25c64_io();
		LCALL 	7FBH 			//0767 	37FB
		MOVLP 	7H 			//0768 	0187

		//;test_61f14x_SPI.C: 206: SPIReadData = SPI_Read(0x12);
		LDWI 	12H 			//0769 	0012
		ORG		076AH
		STR 	73H 			//076A 	10F3
		CLRF 	74H 			//076B 	11F4
		LCALL 	778H 			//076C 	3778
		MOVLP 	7H 			//076D 	0187
		STR 	76H 			//076E 	10F6

		//;test_61f14x_SPI.C: 207: SPI_Write(0x13,~SPIReadData);
		LDWI 	13H 			//076F 	0013
		STR 	73H 			//0770 	10F3
		CLRF 	74H 			//0771 	11F4
		ORG		0772H
		COMR 	76H, 0H 		//0772 	1976
		STR 	75H 			//0773 	10F5
		LCALL 	78CH 			//0774 	378C
		MOVLP 	7H 			//0775 	0187

		//;test_61f14x_SPI.C: 210: {
		//;test_61f14x_SPI.C: 211: __nop();
		NOP 					//0776 	1000
		LJUMP 	776H 			//0777 	3F76

		//;test_61f14x_SPI.C: 166: unsigned char spidata;
		//;test_61f14x_SPI.C: 167: while(SPI_ReadStatus()&0x01);
		LCALL 	7C5H 			//0778 	37C5
		MOVLP 	7H 			//0779 	0187
		ORG		077AH
		ANDWI 	1H 			//077A 	0901
		BTSS 	3H, 2H 			//077B 	2D03
		LJUMP 	778H 			//077C 	3F78

		//;test_61f14x_SPI.C: 168: PB0=0;
		BCR 	DH, 0H 			//077D 	200D

		//;test_61f14x_SPI.C: 169: SPI_RW(0x03);
		LDWI 	3H 			//077E 	0003
		LCALL 	7A9H 			//077F 	37A9
		MOVLP 	7H 			//0780 	0187

		//;test_61f14x_SPI.C: 170: SPI_RW((unsigned char)((addr)>>8));
		LDR 	74H, 0H 			//0781 	1874
		ORG		0782H
		LCALL 	7A9H 			//0782 	37A9
		MOVLP 	7H 			//0783 	0187

		//;test_61f14x_SPI.C: 171: SPI_RW((unsigned char)addr);
		LDR 	73H, 0H 			//0784 	1873
		LCALL 	7A9H 			//0785 	37A9
		MOVLP 	7H 			//0786 	0187

		//;test_61f14x_SPI.C: 172: spidata = SPI_RW(0x00);
		LDWI 	0H 			//0787 	0000
		LCALL 	7A9H 			//0788 	37A9
		STR 	75H 			//0789 	10F5
		ORG		078AH

		//;test_61f14x_SPI.C: 173: PB0=1;
		BSR 	DH, 0H 			//078A 	240D

		//;test_61f14x_SPI.C: 174: return spidata;
		RET 					//078B 	1008

		//;test_61f14x_SPI.C: 183: while(SPI_ReadStatus()&0x01);
		LCALL 	7C5H 			//078C 	37C5
		MOVLP 	7H 			//078D 	0187
		ANDWI 	1H 			//078E 	0901
		BTSS 	3H, 2H 			//078F 	2D03
		LJUMP 	78CH 			//0790 	3F8C

		//;test_61f14x_SPI.C: 184: WriteEnable();
		LCALL 	7F6H 			//0791 	37F6
		ORG		0792H
		MOVLP 	7H 			//0792 	0187

		//;test_61f14x_SPI.C: 185: PB0=0;
		BCR 	DH, 0H 			//0793 	200D

		//;test_61f14x_SPI.C: 186: SPI_RW(0x02);
		LDWI 	2H 			//0794 	0002
		LCALL 	7A9H 			//0795 	37A9
		MOVLP 	7H 			//0796 	0187

		//;test_61f14x_SPI.C: 187: SPI_RW((unsigned char)((addr)>>8));
		LDR 	74H, 0H 			//0797 	1874
		LCALL 	7A9H 			//0798 	37A9
		MOVLP 	7H 			//0799 	0187
		ORG		079AH

		//;test_61f14x_SPI.C: 188: SPI_RW((unsigned char)addr);
		LDR 	73H, 0H 			//079A 	1873
		LCALL 	7A9H 			//079B 	37A9
		MOVLP 	7H 			//079C 	0187

		//;test_61f14x_SPI.C: 190: SPI_RW(dat);
		LDR 	75H, 0H 			//079D 	1875
		LCALL 	7A9H 			//079E 	37A9
		MOVLP 	7H 			//079F 	0187

		//;test_61f14x_SPI.C: 191: PB0=1;
		BSR 	DH, 0H 			//07A0 	240D

		//;test_61f14x_SPI.C: 192: WriteDisable();
		LCALL 	7F1H 			//07A1 	37F1
		ORG		07A2H
		MOVLP 	7H 			//07A2 	0187

		//;test_61f14x_SPI.C: 193: while(SPI_ReadStatus()&0x01);
		LCALL 	7C5H 			//07A3 	37C5
		MOVLP 	7H 			//07A4 	0187
		ANDWI 	1H 			//07A5 	0901
		BTSC 	3H, 2H 			//07A6 	2903
		RET 					//07A7 	1008
		LJUMP 	7A3H 			//07A8 	3FA3
		STR 	71H 			//07A9 	10F1
		ORG		07AAH

		//;test_61f14x_SPI.C: 90: unsigned char i;
		//;test_61f14x_SPI.C: 91: for(i=0;i<8;i++)
		CLRF 	70H 			//07AA 	11F0

		//;test_61f14x_SPI.C: 92: {
		//;test_61f14x_SPI.C: 93: if(data&0x80)
		BTSS 	71H, 7H 		//07AB 	2FF1
		LJUMP 	7AFH 			//07AC 	3FAF

		//;test_61f14x_SPI.C: 94: PB2 = 1;
		BSR 	DH, 2H 			//07AD 	250D
		LJUMP 	7B0H 			//07AE 	3FB0

		//;test_61f14x_SPI.C: 95: else
		//;test_61f14x_SPI.C: 96: PB2 = 0;
		BCR 	DH, 2H 			//07AF 	210D

		//;test_61f14x_SPI.C: 97: __nop();
		NOP 					//07B0 	1000

		//;test_61f14x_SPI.C: 98: data<<=1;
		LSLF 	71H, 1H 		//07B1 	05F1
		ORG		07B2H

		//;test_61f14x_SPI.C: 99: PB5 = 1;
		MOVLB 	0H 			//07B2 	1020
		BSR 	DH, 5H 			//07B3 	268D

		//;test_61f14x_SPI.C: 100: __nop();
		NOP 					//07B4 	1000

		//;test_61f14x_SPI.C: 101: if(PB4)
		MOVLB 	0H 			//07B5 	1020
		BTSS 	DH, 4H 			//07B6 	2E0D
		LJUMP 	7BAH 			//07B7 	3FBA

		//;test_61f14x_SPI.C: 102: data |= 0x01;
		BSR 	71H, 0H 			//07B8 	2471
		LJUMP 	7BBH 			//07B9 	3FBB
		ORG		07BAH

		//;test_61f14x_SPI.C: 103: else
		//;test_61f14x_SPI.C: 104: data &= 0xFE;
		BCR 	71H, 0H 			//07BA 	2071

		//;test_61f14x_SPI.C: 105: __nop();
		NOP 					//07BB 	1000

		//;test_61f14x_SPI.C: 106: PB5 = 0;
		MOVLB 	0H 			//07BC 	1020
		BCR 	DH, 5H 			//07BD 	228D
		LDWI 	8H 			//07BE 	0008
		INCR 	70H, 1H 		//07BF 	1AF0
		SUBWR 	70H, 0H 		//07C0 	1270
		BTSS 	3H, 0H 			//07C1 	2C03
		ORG		07C2H
		LJUMP 	7ABH 			//07C2 	3FAB

		//;test_61f14x_SPI.C: 107: }
		//;test_61f14x_SPI.C: 108: return data;
		LDR 	71H, 0H 			//07C3 	1871
		RET 					//07C4 	1008

		//;test_61f14x_SPI.C: 139: PB0=0;
		BCR 	DH, 0H 			//07C5 	200D

		//;test_61f14x_SPI.C: 140: SPI_RW(0x05);
		LDWI 	5H 			//07C6 	0005
		LCALL 	7A9H 			//07C7 	37A9
		MOVLP 	7H 			//07C8 	0187

		//;test_61f14x_SPI.C: 141: status = SPI_RW(0x00);
		LDWI 	0H 			//07C9 	0000
		ORG		07CAH
		LCALL 	7A9H 			//07CA 	37A9
		STR 	72H 			//07CB 	10F2

		//;test_61f14x_SPI.C: 142: PB0=1;
		BSR 	DH, 0H 			//07CC 	240D

		//;test_61f14x_SPI.C: 143: return status;
		RET 					//07CD 	1008

		//;test_61f14x_SPI.C: 43: OSCCON = 0B01110001;
		LDWI 	71H 			//07CE 	0071
		MOVLB 	1H 			//07CF 	1021
		STR 	19H 			//07D0 	1099

		//;test_61f14x_SPI.C: 44: INTCON = 0;
		CLRF 	BH 			//07D1 	118B
		ORG		07D2H

		//;test_61f14x_SPI.C: 46: PORTA = 0B00000000;
		MOVLB 	0H 			//07D2 	1020
		CLRF 	CH 			//07D3 	118C

		//;test_61f14x_SPI.C: 47: TRISA = 0B00000000;
		MOVLB 	1H 			//07D4 	1021
		CLRF 	CH 			//07D5 	118C

		//;test_61f14x_SPI.C: 48: PORTB = 0B00000000;
		MOVLB 	0H 			//07D6 	1020
		CLRF 	DH 			//07D7 	118D

		//;test_61f14x_SPI.C: 49: TRISB = 0B00010000;
		LDWI 	10H 			//07D8 	0010
		MOVLB 	1H 			//07D9 	1021
		ORG		07DAH
		STR 	DH 			//07DA 	108D

		//;test_61f14x_SPI.C: 50: PORTC = 0B00000000;
		MOVLB 	0H 			//07DB 	1020
		CLRF 	EH 			//07DC 	118E

		//;test_61f14x_SPI.C: 51: TRISC = 0B00000000;
		MOVLB 	1H 			//07DD 	1021
		CLRF 	EH 			//07DE 	118E

		//;test_61f14x_SPI.C: 53: WPUA = 0B00000000;
		MOVLB 	3H 			//07DF 	1023
		CLRF 	CH 			//07E0 	118C

		//;test_61f14x_SPI.C: 54: WPUB = 0B00010000;
		STR 	DH 			//07E1 	108D
		ORG		07E2H

		//;test_61f14x_SPI.C: 55: WPUC = 0B00000000;
		CLRF 	EH 			//07E2 	118E

		//;test_61f14x_SPI.C: 57: WPDA = 0B00000000;
		MOVLB 	4H 			//07E3 	1024
		CLRF 	CH 			//07E4 	118C

		//;test_61f14x_SPI.C: 58: WPDB = 0B00000000;
		CLRF 	DH 			//07E5 	118D

		//;test_61f14x_SPI.C: 59: WPDC = 0B00000000;
		CLRF 	EH 			//07E6 	118E

		//;test_61f14x_SPI.C: 61: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07E7 	00FF
		MOVLB 	2H 			//07E8 	1022
		STR 	1AH 			//07E9 	109A
		ORG		07EAH

		//;test_61f14x_SPI.C: 62: PSRC1 = 0B11111111;
		STR 	1BH 			//07EA 	109B

		//;test_61f14x_SPI.C: 64: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07EB 	1023
		STR 	1AH 			//07EC 	109A

		//;test_61f14x_SPI.C: 65: PSINK1 = 0B11111111;
		STR 	1BH 			//07ED 	109B

		//;test_61f14x_SPI.C: 66: PSINK2 = 0B11111111;
		STR 	1CH 			//07EE 	109C

		//;test_61f14x_SPI.C: 68: ANSELA = 0B00000000;
		CLRF 	17H 			//07EF 	1197
		RET 					//07F0 	1008

		//;test_61f14x_SPI.C: 126: PB0=0;
		BCR 	DH, 0H 			//07F1 	200D
		ORG		07F2H

		//;test_61f14x_SPI.C: 127: SPI_RW(0x04);
		LDWI 	4H 			//07F2 	0004
		LCALL 	7A9H 			//07F3 	37A9

		//;test_61f14x_SPI.C: 128: PB0=1;
		BSR 	DH, 0H 			//07F4 	240D
		RET 					//07F5 	1008

		//;test_61f14x_SPI.C: 116: PB0=0;
		BCR 	DH, 0H 			//07F6 	200D

		//;test_61f14x_SPI.C: 117: SPI_RW(0x06);
		LDWI 	6H 			//07F7 	0006
		LCALL 	7A9H 			//07F8 	37A9

		//;test_61f14x_SPI.C: 118: PB0=1;
		BSR 	DH, 0H 			//07F9 	240D
		ORG		07FAH
		RET 					//07FA 	1008

		//;test_61f14x_SPI.C: 78: PB0 = 1;
		MOVLB 	0H 			//07FB 	1020
		BSR 	DH, 0H 			//07FC 	240D

		//;test_61f14x_SPI.C: 79: PB5 = 0;
		BCR 	DH, 5H 			//07FD 	228D

		//;test_61f14x_SPI.C: 80: PB2 = 0;
		BCR 	DH, 2H 			//07FE 	210D
		RET 					//07FF 	1008
			END
