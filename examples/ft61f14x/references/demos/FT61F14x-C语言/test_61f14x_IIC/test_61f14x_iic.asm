//Deviec:FT61F14X
//-----------------------Variable---------------------------------
		_IICReadData		EQU		77H
//		IIC_WRITE@address		EQU		76H
//		IIC_WRITE@data		EQU		75H
//		IIC_WRITE@address		EQU		C00000H
//		IIC_READ@address		EQU		75H
//		IIC_READ@iicdata		EQU		76H
//		IIC_READ@address		EQU		C00000H
//		IIC_Wait_Ack@ucErrTime		EQU		72H
//		IIC_Send_Byte@txd		EQU		73H
//		IIC_Send_Byte@t		EQU		74H
//		IIC_Send_Byte@txd		EQU		C00000H
//		IIC_Read_Byte@i		EQU		73H
//		IIC_Read_Byte@receive		EQU		72H
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
		MOVLP 	6H 			//0002 	0186
		LJUMP 	6E8H 			//0003 	3EE8
		ORG		06E8H
		MOVLB 	0H 			//06E8 	1020
		LJUMP 	70BH 			//06E9 	3F0B

		//;test_61f14x_IIC.C: 186: PA4=0;
		MOVLB 	0H 			//06EA 	1020
		BCR 	CH, 4H 			//06EB 	220C

		//;test_61f14x_IIC.C: 187: TRISA3 =0;
		MOVLB 	1H 			//06EC 	1021
		BCR 	CH, 3H 			//06ED 	218C

		//;test_61f14x_IIC.C: 188: PA3=1;
		MOVLB 	0H 			//06EE 	1020
		BSR 	CH, 3H 			//06EF 	258C
		ORG		06F0H

		//;test_61f14x_IIC.C: 189: DelayUs(5);
		LDWI 	5H 			//06F0 	0005
		LCALL 	79AH 			//06F1 	379A
		MOVLP 	6H 			//06F2 	0186

		//;test_61f14x_IIC.C: 190: PA4=1;
		MOVLB 	0H 			//06F3 	1020
		BSR 	CH, 4H 			//06F4 	260C

		//;test_61f14x_IIC.C: 191: DelayUs(5);
		LDWI 	5H 			//06F5 	0005
		LCALL 	79AH 			//06F6 	379A

		//;test_61f14x_IIC.C: 192: PA4=0;
		MOVLB 	0H 			//06F7 	1020
		ORG		06F8H
		BCR 	CH, 4H 			//06F8 	220C
		RET 					//06F9 	1008

		//;test_61f14x_IIC.C: 126: TRISA3 =0;
		MOVLB 	1H 			//06FA 	1021
		BCR 	CH, 3H 			//06FB 	218C

		//;test_61f14x_IIC.C: 127: PA4=0;
		MOVLB 	0H 			//06FC 	1020
		BCR 	CH, 4H 			//06FD 	220C

		//;test_61f14x_IIC.C: 128: PA3=0;
		BCR 	CH, 3H 			//06FE 	218C

		//;test_61f14x_IIC.C: 129: DelayUs(10);
		LDWI 	AH 			//06FF 	000A
		ORG		0700H
		LCALL 	79AH 			//0700 	379A
		MOVLP 	6H 			//0701 	0186

		//;test_61f14x_IIC.C: 130: PA4=1;
		MOVLB 	0H 			//0702 	1020
		BSR 	CH, 4H 			//0703 	260C

		//;test_61f14x_IIC.C: 131: DelayUs(10);
		LDWI 	AH 			//0704 	000A
		LCALL 	79AH 			//0705 	379A
		MOVLP 	6H 			//0706 	0186

		//;test_61f14x_IIC.C: 132: PA3=1;
		MOVLB 	0H 			//0707 	1020
		ORG		0708H
		BSR 	CH, 3H 			//0708 	258C

		//;test_61f14x_IIC.C: 133: DelayUs(10);
		LDWI 	AH 			//0709 	000A
		LJUMP 	79AH 			//070A 	3F9A

		//;test_61f14x_IIC.C: 294: POWER_INITIAL();
		LCALL 	7DEH 			//070B 	37DE
		MOVLP 	6H 			//070C 	0186

		//;test_61f14x_IIC.C: 296: IICReadData = IIC_READ(0x12);
		LDWI 	12H 			//070D 	0012
		LCALL 	750H 			//070E 	3750
		MOVLP 	6H 			//070F 	0186
		ORG		0710H
		STR 	77H 			//0710 	10F7

		//;test_61f14x_IIC.C: 297: DelayMs(10);
		LDWI 	AH 			//0711 	000A
		LCALL 	7CDH 			//0712 	37CD
		MOVLP 	6H 			//0713 	0186

		//;test_61f14x_IIC.C: 298: IIC_WRITE(0x13,~IICReadData);
		COMR 	77H, 0H 		//0714 	1977
		STR 	75H 			//0715 	10F5
		LDWI 	13H 			//0716 	0013
		LCALL 	734H 			//0717 	3734
		ORG		0718H
		MOVLP 	6H 			//0718 	0186

		//;test_61f14x_IIC.C: 301: {
		//;test_61f14x_IIC.C: 302: __nop();
		NOP 					//0719 	1000
		LJUMP 	719H 			//071A 	3F19

		//;test_61f14x_IIC.C: 227: unsigned char i,receive=0;
		CLRF 	72H 			//071B 	11F2

		//;test_61f14x_IIC.C: 228: TRISA3 =1;
		MOVLB 	1H 			//071C 	1021
		BSR 	CH, 3H 			//071D 	258C

		//;test_61f14x_IIC.C: 229: for(i=0;i<8;i++ )
		CLRF 	73H 			//071E 	11F3

		//;test_61f14x_IIC.C: 230: {
		//;test_61f14x_IIC.C: 231: PA4=0;
		MOVLB 	0H 			//071F 	1020
		ORG		0720H
		BCR 	CH, 4H 			//0720 	220C

		//;test_61f14x_IIC.C: 232: DelayUs(5);
		LDWI 	5H 			//0721 	0005
		LCALL 	79AH 			//0722 	379A
		MOVLP 	6H 			//0723 	0186

		//;test_61f14x_IIC.C: 233: PA4=1;
		MOVLB 	0H 			//0724 	1020
		BSR 	CH, 4H 			//0725 	260C

		//;test_61f14x_IIC.C: 234: receive<<=1;
		LSLF 	72H, 1H 		//0726 	05F2

		//;test_61f14x_IIC.C: 235: if(PA3)receive++;
		BTSC 	CH, 3H 			//0727 	298C
		ORG		0728H
		INCR 	72H, 1H 		//0728 	1AF2

		//;test_61f14x_IIC.C: 236: DelayUs(5);
		LDWI 	5H 			//0729 	0005
		LCALL 	79AH 			//072A 	379A
		MOVLP 	6H 			//072B 	0186
		LDWI 	8H 			//072C 	0008
		INCR 	73H, 1H 		//072D 	1AF3
		SUBWR 	73H, 0H 		//072E 	1273
		BTSS 	3H, 0H 			//072F 	2C03
		ORG		0730H
		LJUMP 	71FH 			//0730 	3F1F

		//;test_61f14x_IIC.C: 237: }
		//;test_61f14x_IIC.C: 238: IIC_NAck();
		LCALL 	6EAH 			//0731 	36EA

		//;test_61f14x_IIC.C: 240: return receive;
		LDR 	72H, 0H 			//0732 	1872
		RET 					//0733 	1008
		STR 	76H 			//0734 	10F6

		//;test_61f14x_IIC.C: 272: IIC_WRITE_Begin:
		//;test_61f14x_IIC.C: 273: IIC_Start();
		LCALL 	7BCH 			//0735 	37BC
		MOVLP 	6H 			//0736 	0186

		//;test_61f14x_IIC.C: 274: IIC_Send_Byte(0xa0);
		LDWI 	A0H 			//0737 	00A0
		ORG		0738H
		LCALL 	773H 			//0738 	3773
		MOVLP 	6H 			//0739 	0186

		//;test_61f14x_IIC.C: 275: if(IIC_Wait_Ack())goto IIC_WRITE_Begin;
		LCALL 	7A3H 			//073A 	37A3
		MOVLP 	6H 			//073B 	0186
		XORWI 	0H 			//073C 	0A00
		BTSS 	3H, 2H 			//073D 	2D03
		LJUMP 	735H 			//073E 	3F35

		//;test_61f14x_IIC.C: 277: IIC_Send_Byte(address);
		LDR 	76H, 0H 			//073F 	1876
		ORG		0740H
		LCALL 	773H 			//0740 	3773
		MOVLP 	6H 			//0741 	0186

		//;test_61f14x_IIC.C: 278: if(IIC_Wait_Ack())goto IIC_WRITE_Begin;
		LCALL 	7A3H 			//0742 	37A3
		MOVLP 	6H 			//0743 	0186
		XORWI 	0H 			//0744 	0A00
		BTSS 	3H, 2H 			//0745 	2D03
		LJUMP 	735H 			//0746 	3F35

		//;test_61f14x_IIC.C: 280: IIC_Send_Byte(data);
		LDR 	75H, 0H 			//0747 	1875
		ORG		0748H
		LCALL 	773H 			//0748 	3773
		MOVLP 	6H 			//0749 	0186

		//;test_61f14x_IIC.C: 281: if(IIC_Wait_Ack())goto IIC_WRITE_Begin;
		LCALL 	7A3H 			//074A 	37A3
		MOVLP 	6H 			//074B 	0186
		XORWI 	0H 			//074C 	0A00
		BTSS 	3H, 2H 			//074D 	2D03
		LJUMP 	735H 			//074E 	3F35

		//;test_61f14x_IIC.C: 283: IIC_Stop();
		LJUMP 	6FAH 			//074F 	3EFA
		ORG		0750H
		STR 	75H 			//0750 	10F5

		//;test_61f14x_IIC.C: 252: IIC_Start();
		LCALL 	7BCH 			//0751 	37BC
		MOVLP 	6H 			//0752 	0186

		//;test_61f14x_IIC.C: 253: IIC_Send_Byte(0xa0);
		LDWI 	A0H 			//0753 	00A0
		LCALL 	773H 			//0754 	3773
		MOVLP 	6H 			//0755 	0186

		//;test_61f14x_IIC.C: 254: if(IIC_Wait_Ack())goto IIC_READ_Begin;
		LCALL 	7A3H 			//0756 	37A3
		MOVLP 	6H 			//0757 	0186
		ORG		0758H
		XORWI 	0H 			//0758 	0A00
		BTSS 	3H, 2H 			//0759 	2D03
		LJUMP 	751H 			//075A 	3F51

		//;test_61f14x_IIC.C: 255: IIC_Send_Byte(address);
		LDR 	75H, 0H 			//075B 	1875
		LCALL 	773H 			//075C 	3773
		MOVLP 	6H 			//075D 	0186

		//;test_61f14x_IIC.C: 256: if(IIC_Wait_Ack())goto IIC_READ_Begin;
		LCALL 	7A3H 			//075E 	37A3
		MOVLP 	6H 			//075F 	0186
		ORG		0760H
		XORWI 	0H 			//0760 	0A00
		BTSS 	3H, 2H 			//0761 	2D03
		LJUMP 	751H 			//0762 	3F51

		//;test_61f14x_IIC.C: 257: IIC_Start();
		LCALL 	7BCH 			//0763 	37BC
		MOVLP 	6H 			//0764 	0186

		//;test_61f14x_IIC.C: 258: IIC_Send_Byte(0xa1);
		LDWI 	A1H 			//0765 	00A1
		LCALL 	773H 			//0766 	3773
		MOVLP 	6H 			//0767 	0186
		ORG		0768H

		//;test_61f14x_IIC.C: 259: if(IIC_Wait_Ack())goto IIC_READ_Begin;
		LCALL 	7A3H 			//0768 	37A3
		MOVLP 	6H 			//0769 	0186
		XORWI 	0H 			//076A 	0A00
		BTSS 	3H, 2H 			//076B 	2D03
		LJUMP 	751H 			//076C 	3F51

		//;test_61f14x_IIC.C: 260: iicdata=IIC_Read_Byte();
		LCALL 	71BH 			//076D 	371B
		MOVLP 	6H 			//076E 	0186
		STR 	76H 			//076F 	10F6
		ORG		0770H

		//;test_61f14x_IIC.C: 261: IIC_Stop();
		LCALL 	6FAH 			//0770 	36FA

		//;test_61f14x_IIC.C: 262: return iicdata;
		LDR 	76H, 0H 			//0771 	1876
		RET 					//0772 	1008
		STR 	73H 			//0773 	10F3

		//;test_61f14x_IIC.C: 202: unsigned char t;
		//;test_61f14x_IIC.C: 203: TRISA3 =0;
		MOVLB 	1H 			//0774 	1021
		BCR 	CH, 3H 			//0775 	218C

		//;test_61f14x_IIC.C: 204: PA4=0;
		MOVLB 	0H 			//0776 	1020
		BCR 	CH, 4H 			//0777 	220C
		ORG		0778H

		//;test_61f14x_IIC.C: 205: for(t=0;t<8;t++)
		CLRF 	74H 			//0778 	11F4

		//;test_61f14x_IIC.C: 206: {
		//;test_61f14x_IIC.C: 207: if((txd&0x80)>>7)
		LDR 	73H, 0H 			//0779 	1873
		STR 	72H 			//077A 	10F2
		LDWI 	7H 			//077B 	0007
		LSRF 	72H, 1H 		//077C 	06F2
		DECRSZ 	9H, 1H 		//077D 	1B89
		LJUMP 	77CH 			//077E 	3F7C
		BTSS 	72H, 0H 		//077F 	2C72
		ORG		0780H
		LJUMP 	784H 			//0780 	3F84

		//;test_61f14x_IIC.C: 208: PA3=1;
		MOVLB 	0H 			//0781 	1020
		BSR 	CH, 3H 			//0782 	258C
		LJUMP 	786H 			//0783 	3F86

		//;test_61f14x_IIC.C: 209: else
		//;test_61f14x_IIC.C: 210: PA3=0;
		MOVLB 	0H 			//0784 	1020
		BCR 	CH, 3H 			//0785 	218C
		LDWI 	5H 			//0786 	0005

		//;test_61f14x_IIC.C: 211: txd<<=1;
		LSLF 	73H, 1H 		//0787 	05F3
		ORG		0788H

		//;test_61f14x_IIC.C: 212: DelayUs(5);
		LCALL 	79AH 			//0788 	379A
		MOVLP 	6H 			//0789 	0186

		//;test_61f14x_IIC.C: 213: PA4=1;
		MOVLB 	0H 			//078A 	1020
		BSR 	CH, 4H 			//078B 	260C

		//;test_61f14x_IIC.C: 214: DelayUs(5);
		LDWI 	5H 			//078C 	0005
		LCALL 	79AH 			//078D 	379A
		MOVLP 	6H 			//078E 	0186

		//;test_61f14x_IIC.C: 215: PA4=0;
		MOVLB 	0H 			//078F 	1020
		ORG		0790H
		BCR 	CH, 4H 			//0790 	220C

		//;test_61f14x_IIC.C: 216: DelayUs(5);
		LDWI 	5H 			//0791 	0005
		LCALL 	79AH 			//0792 	379A
		MOVLP 	6H 			//0793 	0186
		LDWI 	8H 			//0794 	0008
		INCR 	74H, 1H 		//0795 	1AF4
		SUBWR 	74H, 0H 		//0796 	1274
		BTSC 	3H, 0H 			//0797 	2803
		ORG		0798H
		RET 					//0798 	1008
		LJUMP 	779H 			//0799 	3F79
		STR 	70H 			//079A 	10F0

		//;test_61f14x_IIC.C: 78: unsigned char a;
		//;test_61f14x_IIC.C: 79: for(a=0;a<Time;a++)
		CLRF 	71H 			//079B 	11F1
		LDR 	70H, 0H 			//079C 	1870
		SUBWR 	71H, 0H 		//079D 	1271
		BTSC 	3H, 0H 			//079E 	2803
		RET 					//079F 	1008
		ORG		07A0H

		//;test_61f14x_IIC.C: 80: {
		//;test_61f14x_IIC.C: 81: __nop();
		NOP 					//07A0 	1000
		INCR 	71H, 1H 		//07A1 	1AF1
		LJUMP 	79CH 			//07A2 	3F9C

		//;test_61f14x_IIC.C: 144: unsigned char ucErrTime=0;
		CLRF 	72H 			//07A3 	11F2

		//;test_61f14x_IIC.C: 145: TRISA3 =1;
		MOVLB 	1H 			//07A4 	1021
		BSR 	CH, 3H 			//07A5 	258C

		//;test_61f14x_IIC.C: 146: PA3=1;
		MOVLB 	0H 			//07A6 	1020
		BSR 	CH, 3H 			//07A7 	258C
		ORG		07A8H

		//;test_61f14x_IIC.C: 147: DelayUs(5);
		LDWI 	5H 			//07A8 	0005
		LCALL 	79AH 			//07A9 	379A
		MOVLP 	6H 			//07AA 	0186

		//;test_61f14x_IIC.C: 148: PA4=1;
		MOVLB 	0H 			//07AB 	1020
		BSR 	CH, 4H 			//07AC 	260C

		//;test_61f14x_IIC.C: 149: DelayUs(5);
		LDWI 	5H 			//07AD 	0005
		LCALL 	79AH 			//07AE 	379A
		MOVLP 	6H 			//07AF 	0186
		ORG		07B0H

		//;test_61f14x_IIC.C: 150: while(PA3)
		MOVLB 	0H 			//07B0 	1020
		BTSS 	CH, 3H 			//07B1 	2D8C
		LJUMP 	7BAH 			//07B2 	3FBA
		LDWI 	FBH 			//07B3 	00FB

		//;test_61f14x_IIC.C: 151: {
		//;test_61f14x_IIC.C: 152: ucErrTime++;
		INCR 	72H, 1H 		//07B4 	1AF2

		//;test_61f14x_IIC.C: 153: if(ucErrTime>250)
		SUBWR 	72H, 0H 		//07B5 	1272
		BTSS 	3H, 0H 			//07B6 	2C03
		LJUMP 	7B0H 			//07B7 	3FB0
		ORG		07B8H

		//;test_61f14x_IIC.C: 154: {
		//;test_61f14x_IIC.C: 155: IIC_Stop();
		LCALL 	6FAH 			//07B8 	36FA

		//;test_61f14x_IIC.C: 156: return 1;
		RETW 	1H 			//07B9 	0401

		//;test_61f14x_IIC.C: 157: }
		//;test_61f14x_IIC.C: 158: }
		//;test_61f14x_IIC.C: 159: PA4=0;
		BCR 	CH, 4H 			//07BA 	220C

		//;test_61f14x_IIC.C: 160: return 0;
		RETW 	0H 			//07BB 	0400

		//;test_61f14x_IIC.C: 109: TRISA3 =0;
		MOVLB 	1H 			//07BC 	1021
		BCR 	CH, 3H 			//07BD 	218C

		//;test_61f14x_IIC.C: 110: PA3=1;
		MOVLB 	0H 			//07BE 	1020
		BSR 	CH, 3H 			//07BF 	258C
		ORG		07C0H

		//;test_61f14x_IIC.C: 111: PA4=1;
		BSR 	CH, 4H 			//07C0 	260C

		//;test_61f14x_IIC.C: 112: DelayUs(10);
		LDWI 	AH 			//07C1 	000A
		LCALL 	79AH 			//07C2 	379A
		MOVLP 	6H 			//07C3 	0186

		//;test_61f14x_IIC.C: 113: PA3=0;
		MOVLB 	0H 			//07C4 	1020
		BCR 	CH, 3H 			//07C5 	218C

		//;test_61f14x_IIC.C: 114: DelayUs(10);
		LDWI 	AH 			//07C6 	000A
		LCALL 	79AH 			//07C7 	379A
		ORG		07C8H
		MOVLP 	6H 			//07C8 	0186

		//;test_61f14x_IIC.C: 115: PA4=0;
		MOVLB 	0H 			//07C9 	1020
		BCR 	CH, 4H 			//07CA 	220C

		//;test_61f14x_IIC.C: 116: DelayUs(10);
		LDWI 	AH 			//07CB 	000A
		LJUMP 	79AH 			//07CC 	3F9A
		STR 	72H 			//07CD 	10F2

		//;test_61f14x_IIC.C: 92: unsigned char a,b;
		//;test_61f14x_IIC.C: 93: for(a=0;a<Time;a++)
		CLRF 	73H 			//07CE 	11F3
		LDR 	72H, 0H 			//07CF 	1872
		ORG		07D0H
		SUBWR 	73H, 0H 		//07D0 	1273
		BTSC 	3H, 0H 			//07D1 	2803
		RET 					//07D2 	1008

		//;test_61f14x_IIC.C: 94: {
		//;test_61f14x_IIC.C: 95: for(b=0;b<5;b++)
		CLRF 	74H 			//07D3 	11F4

		//;test_61f14x_IIC.C: 96: {
		//;test_61f14x_IIC.C: 97: DelayUs(197);
		LDWI 	C5H 			//07D4 	00C5
		LCALL 	79AH 			//07D5 	379A
		MOVLP 	6H 			//07D6 	0186
		LDWI 	5H 			//07D7 	0005
		ORG		07D8H
		INCR 	74H, 1H 		//07D8 	1AF4
		SUBWR 	74H, 0H 		//07D9 	1274
		BTSS 	3H, 0H 			//07DA 	2C03
		LJUMP 	7D4H 			//07DB 	3FD4
		INCR 	73H, 1H 		//07DC 	1AF3
		LJUMP 	7CFH 			//07DD 	3FCF

		//;test_61f14x_IIC.C: 43: OSCCON = 0B01110001;
		LDWI 	71H 			//07DE 	0071
		MOVLB 	1H 			//07DF 	1021
		ORG		07E0H
		STR 	19H 			//07E0 	1099

		//;test_61f14x_IIC.C: 44: INTCON = 0;
		CLRF 	BH 			//07E1 	118B

		//;test_61f14x_IIC.C: 46: PORTA = 0B00000000;
		MOVLB 	0H 			//07E2 	1020
		CLRF 	CH 			//07E3 	118C

		//;test_61f14x_IIC.C: 47: TRISA = 0B00000000;
		MOVLB 	1H 			//07E4 	1021
		CLRF 	CH 			//07E5 	118C

		//;test_61f14x_IIC.C: 48: PORTB = 0B00000000;
		MOVLB 	0H 			//07E6 	1020
		CLRF 	DH 			//07E7 	118D
		ORG		07E8H

		//;test_61f14x_IIC.C: 49: TRISB = 0B00000000;
		MOVLB 	1H 			//07E8 	1021
		CLRF 	DH 			//07E9 	118D

		//;test_61f14x_IIC.C: 50: PORTC = 0B00000000;
		MOVLB 	0H 			//07EA 	1020
		CLRF 	EH 			//07EB 	118E

		//;test_61f14x_IIC.C: 51: TRISC = 0B00000000;
		MOVLB 	1H 			//07EC 	1021
		CLRF 	EH 			//07ED 	118E

		//;test_61f14x_IIC.C: 53: WPUA = 0B00000000;
		MOVLB 	3H 			//07EE 	1023
		CLRF 	CH 			//07EF 	118C
		ORG		07F0H

		//;test_61f14x_IIC.C: 54: WPUB = 0B00000000;
		CLRF 	DH 			//07F0 	118D

		//;test_61f14x_IIC.C: 55: WPUC = 0B00000000;
		CLRF 	EH 			//07F1 	118E

		//;test_61f14x_IIC.C: 57: WPDA = 0B00000000;
		MOVLB 	4H 			//07F2 	1024
		CLRF 	CH 			//07F3 	118C

		//;test_61f14x_IIC.C: 58: WPDB = 0B00000000;
		CLRF 	DH 			//07F4 	118D

		//;test_61f14x_IIC.C: 59: WPDC = 0B00000000;
		CLRF 	EH 			//07F5 	118E

		//;test_61f14x_IIC.C: 61: PSRC0 = 0B11111111;
		LDWI 	FFH 			//07F6 	00FF
		MOVLB 	2H 			//07F7 	1022
		ORG		07F8H
		STR 	1AH 			//07F8 	109A

		//;test_61f14x_IIC.C: 62: PSRC1 = 0B11111111;
		STR 	1BH 			//07F9 	109B

		//;test_61f14x_IIC.C: 64: PSINK0 = 0B11111111;
		MOVLB 	3H 			//07FA 	1023
		STR 	1AH 			//07FB 	109A

		//;test_61f14x_IIC.C: 65: PSINK1 = 0B11111111;
		STR 	1BH 			//07FC 	109B

		//;test_61f14x_IIC.C: 66: PSINK2 = 0B11111111;
		STR 	1CH 			//07FD 	109C

		//;test_61f14x_IIC.C: 68: ANSELA = 0B00000000;
		CLRF 	17H 			//07FE 	1197
		RET 					//07FF 	1008
			END
