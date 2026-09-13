# Makefile (metropolis-kr 슬라이드) — XeLaTeX + kotex 빌드.
#   make            1회 빌드 (main.pdf)
#   make watch      변경 감지 자동 재빌드
#   make clean      보조파일 정리 (PDF 유지)
#   make distclean  PDF 포함 정리
LATEXMK ?= latexmk
FLAGS    = -xelatex -synctex=1 -interaction=nonstopmode -file-line-error
FILE    ?= $(wildcard *.tex)

.PHONY: all watch clean distclean
all:
	$(LATEXMK) $(FLAGS) $(FILE)
watch:
	$(LATEXMK) $(FLAGS) -pvc $(FILE)
clean:
	$(LATEXMK) -c $(FILE)
distclean:
	$(LATEXMK) -C $(FILE)
