
.PHONY: clean dist docs test upload


clean:
	$(RM) -vr ./build ./dist ./PythonOberon.egg-info ./docs/build
	$(RM) -r $(TESTDIR)
	$(RM) -vr oberon/*.pyc


dist:
	python ./setup.py sdist
	twine check ./dist/*


docs:
	$(MAKE) -C docs html


# In order to support testing the code as installed create a virtualenv
# and install the source dist zip there.
TESTDIR=./TEST00

test: dist
	$(RM) -r $(TESTDIR)
	mkdir $(TESTDIR)
	virtualenv --system-site-packages --never-download $(TESTDIR)/venv
	. $(TESTDIR)/venv/bin/activate && \
		$(TESTDIR)/venv/bin/pip install --no-cache-dir --no-index \
		    ./dist/PythonOberon-*.tar.gz
	echo "Type: cd $(TESTDIR) ; source ./venv/bin/activate"


# Upload to test server only.
PYPI_REPO=testpypi

upload: dist
	twine upload -r $(PYPI_REPO) ./dist/*


# To install from the test PyPI server.
# pip install -i https://test.pypi.org/simple/ --no-deps PythonOberon


