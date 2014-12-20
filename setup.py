#!/usr/bin/env python

from distutils.core import setup

setup(name='port-agent-antelope',
      version='0.0.1',
      description='OOI-CI port agent for Antelope ORBs',
      author='OOI-CI',
      author_email='contactooici@oceanobservatories.org',
      url='https://github.com/ooici/port-agent-antelope',
      packages=['port_agent'],
      scripts=['port_agent_antelope'],
     )

