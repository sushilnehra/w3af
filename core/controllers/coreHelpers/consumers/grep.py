'''
grep.py

Copyright 2012 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import multiprocessing
import time
import sys

from .constants import FINISH_CONSUMER

from core.controllers.coreHelpers.exception_handler import exception_handler
from core.controllers.coreHelpers.status import w3af_core_status
from core.controllers.exception_handling.helpers import pprint_plugins

from core.data.kb.knowledgeBase import KnowledgeBaseClient


class grep(multiprocessing.Process):
    '''
    Consumer thread that takes requests and responses from the queue and
    analyzes them using user-configured grep plugins.
    '''
    
    def __init__(self, in_queue, grep_plugins, w3af_core):
        '''
        @param in_queue: The input queue that will feed the grep plugins
        @param grep_plugins: Instances of grep plugins in a list
        @param w3af_core: The w3af core that we'll use for status reporting
        '''
        super(grep, self).__init__()
        
        self._in_queue = in_queue
        self._grep_plugins = grep_plugins
        self._w3af_core = w3af_core
        
        # Start a client so I can access the KB from within this process
        # the server was started in w3afCore.py
        kb_client = KnowledgeBaseClient()
        kb_client.start_client()
    
    def run(self):
        '''
        Consume the queue items
        '''
        while True:
           
            request, response = self._in_queue.get()

            if request == response == FINISH_CONSUMER:
                
                for plugin in self._grep_plugins:
                    plugin.end()
                break
                
            else:
                for grep_plugin in self._grep_plugins:
                    try:
                        grep_plugin.grep( request, response )
                    except Exception, e:
                        # Smart error handling, much better than just crashing.
                        # Doing this here and not with something similar to:
                        # sys.excepthook = handle_crash because we want to handle
                        # plugin exceptions in this way, and not framework 
                        # exceptions
                        class fake_status(w3af_core_status):
                            pass
            
                        status = fake_status()
                        status.set_running_plugin( grep_plugin.getName() )
                        status.set_phase( 'grep' )
                        status.set_current_fuzzable_request( request )
                        
                        exec_info = sys.exc_info()
                        enabled_plugins = pprint_plugins(self._w3af_core)
                        exception_handler.handle( status, e , exec_info, enabled_plugins )
    
    def stop(self):
        '''
        Poison the loop
        '''
        self._in_queue.put( (FINISH_CONSUMER, FINISH_CONSUMER) )
        #
        #    Allow some time for the plugins to properly end before anything
        #    else is done at the core level.
        #
        time.sleep(0.5)
        
