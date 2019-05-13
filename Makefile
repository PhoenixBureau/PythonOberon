
.PHONY: clean dist docs test upload


PYPI_REPO=testpypi
TESTDIR=./TEST00


clean:
	$(RM) -vr ./build ./dist ./PythonOberon.egg-info ./docs/build
	$(RM) -r $(TESTDIR)


dist:
	python ./setup.py sdist bdist_wheel
	twine check dist/*


docs:
	$(MAKE) -C docs html


upload: dist
	twine upload -r $(PYPI_REPO) ./dist/*


# In order to support testing the code as installed
# create a virtualenv and install the source dist zip there.
test: dist
	$(RM) -r $(TESTDIR)
	mkdir $(TESTDIR)
	virtualenv --system-site-packages --never-download $(TESTDIR)/venv
	. $(TESTDIR)/venv/bin/activate && \
		$(TESTDIR)/venv/bin/pip install --no-cache-dir --no-index \
		    ./dist/PythonOberon-*.tar.gz
	echo "Type: cd $(TESTDIR) ; source ./venv/bin/activate"


# To install from the test PyPI server.
# pip install -i https://test.pypi.org/simple/ --no-deps PythonOberon