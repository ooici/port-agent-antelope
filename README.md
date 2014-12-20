port-agent-antelope
===================

Port Agent For Antelope


Deployment
----------

These are suggested instructions using virtualenv. Virtualenv is not required,
it's just convenient.

The antelope python packages ship with, and require the use of, the antelope
python distribution. This normally lives somewhere like
`/opt/antelope/python2.7.2`. So create the virtual environment something like
this:

    virtualenv --python=/opt/antelope/5.3/bin/python ve

The antelope library bindings python packages don't live under the antelope
python interpreter, but rather somewhere like
`/opt/antelope/5.3/data/python`. Somehow you have to get that on your python
path. I like to add a `.pth` file to `ve/lib/python2.7/site-packages` which
points to the antelope python package dir. Something like:

	echo /opt/antelope/5.3/data/python > ve/lib/python2.7/site-packages/antelope5.3.pth

Before activating the virtual environment, source the Antelope environment set
up script. This sets up a bunch of important environment variables. (Is this really 
important?) E.g.:

    . /opt/antelope/5.3/setup.sh

Now activate the VE and install the other dependencies. Note that building
gevent from source requires cython; you might want to pip install that if it's
not already on your system.

    . ve/bin/activate
    pip install python-daemon
    pip install git+git://github.com/ooici/utilities.git#egg=Package
    pip install git+git://github.com/surfly/gevent.git@1.0rc2#egg=Package

Now it should be possible to run the port agent.

    ./port_agent_antelope -c config_test -s

You can test it by sending it a command from another shell:

	./port_agent_antelope -c config_test -C ping
	RX Packet:  Type: 4, Timestamp: 3577658548.7, Data: bytearray(b'pong. version: port-agent-antelope 0.0.1')

You should see a reply packet with the port agent version number.

Environment
-----------

The port agent requires that the `ANTELOPE_PYTHON_GILRELEASE` environment
variable bet set so that calls into the Antelope API will not block other
Python threads. This is not set by default when you source the Antelope
environment script.

The `port_agent_antelope` wrapper script sets this variable before it executes
the port agent program. If you wish to import parts of the port agent into
other Python programs or run the tests then you may have to set this variable
explicitly in your environment.

    export ANTELOPE_PYTHON_GILRELEASE=1

Dependencies
------------

### Build Time

* git
* cython

### Installation (recommended)

* git
* virtualenv (system virtualenv OK)
* pip (Comes with virtualenv)

### Run Time

* Antelope 5.3 (Includes Python 2.7 & Antelope Python bindings)
* gevent==1.0dev (1.0rc2)
* greenlet==0.4.0
* lockfile==0.9.1
* python-daemon==1.6
* utilities==2013.05.01 (OOICI utilities)
* PyYAML==3.10
* graypy==0.2.8

These are the versions I developed against. They may not be critical.

gevent is the only dependency that I know requires a particular version, 1.0rc2
from github. Newer version may work as well. Older versions will not as they
lack the `threadpool` module.

