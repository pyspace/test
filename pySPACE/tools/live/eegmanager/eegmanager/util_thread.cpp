/**
 *  Copyright 2011, DFKI GmbH Robotics Innovation Center
 *
 *  This file is part of the MARS simulation framework.
 *
 *  MARS is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU Lesser General Public License
 *  as published by the Free Software Foundation, either version 3
 *  of the License, or (at your option) any later version.
 *
 *  MARS is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with MARS.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "util_thread.h"
#include "utils.h"

#include <ctime>


//namespace mars {

  Mutex Thread::threadListMutex;
  std::list<Thread*> Thread::threads;
  
  Thread::Thread() {
    running = false;
    finished = false;
    // set default stackSize
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_getstacksize(&attr, &myStackSize);
    pthread_attr_destroy(&attr);
    threadListMutex.lock();
    threads.push_back(this);
    threadListMutex.unlock();
  }

  Thread::~Thread() {
    std::list<Thread*>::iterator it;
    threadListMutex.lock();
    for(it = threads.begin(); it != threads.end(); ++it) {
      if(*it == this) {
        threads.erase(it);
        break;
      }
    }
    threadListMutex.unlock();    
  }

  void Thread::setStackSize(std::size_t stackSize) {
    // we can only modify the stackSize as long as we're not running yet
    if (!running) {
      if (stackSize) {
        myStackSize = stackSize;
      } else {
        // reset default stackSize
        pthread_attr_t attr;
        pthread_attr_init(&attr);
        pthread_attr_getstacksize(&attr, &myStackSize);
        pthread_attr_destroy(&attr);        
      }
    }
  }

  void Thread::start() {
    running = true;
    pthread_attr_t threadAttributes;
    pthread_attr_init(&threadAttributes);
    pthread_attr_setdetachstate(&threadAttributes, PTHREAD_CREATE_JOINABLE);
    pthread_attr_setstacksize(&threadAttributes, myStackSize);
    int rc = pthread_create(&myThread, &threadAttributes, 
                            &Thread::runHelper, static_cast<void*>(this));
    pthread_attr_destroy(&threadAttributes);
    if(rc) {
      // TODO: Handle Error!
    }
  }

  void *Thread::runHelper(void *context) {
    Thread *thread = static_cast<Thread*>(context);
    thread->run();
    thread->running = false;
    thread->finished = true;
    return thread;
  }

  bool Thread::wait() {
    void *status;
    int rc = pthread_join(myThread, &status);
    if(rc) {
    	// TODO: handle error
    }
    return true;
  }

  bool Thread::wait(unsigned long timeoutMilliseconds) {
    long timeout = getTime() + timeoutMilliseconds;
    while(running && getTime() < timeout) {
      msleep(1);
    }
    return !running;
  }

  bool Thread::isRunning() const {
    return running;
  }

  bool Thread::isFinished() const {
    return finished;
  }

  std::size_t Thread::getStackSize() const {
    return myStackSize;
  }

  Thread* Thread::getCurrentThread() {
    std::list<Thread*>::iterator it;
    pthread_t thisThreadID = pthread_self();

    for(it = threads.begin(); it != threads.end(); ++it) {
      if(pthread_equal(thisThreadID, (*it)->myThread) == 0) {
        return *it;
      }
    }
    return NULL;
  }

//} // namespace mars
