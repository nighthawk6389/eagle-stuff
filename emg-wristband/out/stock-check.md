# JLCPCB stock and assembly-type check

Read from jlcpcb.com part pages on 2026-11-28 by `tools/stock_report.py`, for 2 boards.

| LCSC | Part (JLCPCB page) | Package | Used as | Per board | Stock | Library | Assembly type | Unit USD | OK |
|---|---|---|---|---|---|---|---|---|---|
| C52923 | CL05A105KA5NQNC (Samsung Electro-Mechanics) | 0402 | 1u | 16 | 10794693 | Basic | Economic and Standard | 0.0046 | yes |
| C1525 | CL05B104KO5NNNC (Samsung Electro-Mechanics) | 0402 | 100n | 23 | 27738188 | Basic | Economic and Standard | 0.0029 | yes |
| C1567 | 0402CG470J500NT (FH (Guangdong Fenghua Advanced Tech)) | 0402 | 47p | 32 | 668339 | Basic | Economic and Standard | 0.0019 | yes |
| C19702 | CL10A106KP8NNNC (Samsung Electro-Mechanics) | 0603 | 10u | 2 | 12595274 | Basic | Economic and Standard | 0.0112 | yes |
| C117031 | T491B226M010AT (KEMET) | CASE-B-3528-21(mm) | 22u | 2 | 2161 | Extended | Economic and Standard | 0.4167 | yes |
| C1523 | 0402B102K500NT (FH (Guangdong Fenghua Advanced Tech)) | 0402 | 1n | 2 | 3120818 | Basic | Economic and Standard | 0.0016 | yes |
| C1595 | 0603B152K500NT (FH (Guangdong Fenghua Advanced Tech)) | 0603 | 1n5 | 1 | 177221 | Extended | Economic and Standard | 0.0044 | yes |
| C8598 | B5819W SL (Jiangsu Changjing Electronics Technology Co., Ltd.) | SOD-123 | B5819W | 1 | 1571344 | Basic | Economic and Standard | 0.0237 | yes |
| C295747 | S2B-PH-SM4-TB(LF)(SN) (JST) | SMD,P=2mm,Surface Mount，Right Angle | S2B-PH-SM4-TB | 1 | 11768 | Extended | Economic and Standard | 0.2039 | yes |
| C596730 | FH12-20S-0.5SH(55) (HRS(Hirose)) | SMD,P=0.5mm,Surface Mount，Right Angle | FH12-20S-0.5SH | 2 | 4045 | Extended | Economic and Standard | 0.5725 | yes |
| C20917 | AO3400A (Alpha & Omega Semicon) | SOT-23 | AO3400A | 2 | 1286866 | Basic | Economic and Standard | 0.078 | yes |
| C11702 | 0402WGF1001TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 1k | 1 | 24951973 | Basic | Economic and Standard | 0.0011 | yes |
| C25744 | 0402WGF1002TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 10k | 3 | 30758956 | Basic | Economic and Standard | 0.0009 | yes |
| C17445 | 0805W8F120JT5E (UNI-ROYAL(Uniroyal Elec)) | 0805 | 12R | 1 | 24997 | Extended | Economic and Standard | 0.0041 | yes |
| C25741 | 0402WGF1003TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 100k | 6 | 10800149 | Basic | Economic and Standard | 0.0009 | yes |
| C25105 | 0402WGF330JTCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 33R | 4 | 3738793 | Basic | Economic and Standard | 0.0011 | yes |
| C17168 | 0402WGF0000TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 0R | 4 | 11842861 | Basic | Economic and Standard | 0.0012 | yes |
| C26083 | 0402WGF1004TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 1M | 1 | 3023878 | Basic | Economic and Standard | 0.001 | yes |
| C25792 | 0402WGF4702TCE (UNI-ROYAL(Uniroyal Elec)) | 0402 | 47k | 1 | 4682667 | Basic | Economic and Standard | 0.0019 | yes |
| C2028 | 4D02WGJ0473TCE (UNI-ROYAL(Uniroyal Elec)) | 0402x4 | 47k x4 | 8 | 6318 | Extended | Economic and Standard | 0.006 | yes |
| C17401557 | 102010469 (Seeed) | SMD,21x17.8mm | XIAO nRF52840 Sense | 1 | 120 | Extended | Standard Only | 18.5918 | yes |
| C475492 | LP5907MFX-3.0/NOPB (Texas Instruments) | SOT-23-5 | LP5907MFX-3.0 | 1 | 24484 | Extended | Economic and Standard | 0.2789 | yes |
| C527440 | ADS1298IPAGR (Texas Instruments) | TQFP-64(10x10) | ADS1298IPAGR | 2 | 2345 | Extended | Economic and Standard | 19.8057 | yes |
| C527516 | TPD4E001DRLR (Texas Instruments) | SOT-563 | TPD4E001DRL | 10 | 3972 | Extended | Economic and Standard | 0.4187 | yes |

24 BOM lines, 10 of them extended parts (JLCPCB charges a fee per extended part type).
Parts that force Standard assembly: C17401557 (XIAO nRF52840 Sense).
Not on the BOM: the test points and the motor pads (bare copper), and the motor itself.
