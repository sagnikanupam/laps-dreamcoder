.PHONY: solvers

all:
	cd solvers && \
	  dune build @install --profile=release && \
	  dune install --sections bin --bindir=`pwd`/../
	ln -fs ../../logoDrawString data/geom/logoDrawString

clean:
	rm -f clevrSolver clevrTest compression helmholtz logoDrawString \
	  protonet_tester re2Test solver test_clevr_primitives versionDemo \
	  data/geom/logoDrawString
	cd solvers && dune clean
