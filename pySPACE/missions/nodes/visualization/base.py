""" Base class for visualization nodes

**Classes**
 
 :VisualizationBase: 
     This node can be used as a base to visualize instances of the data as
     time series. To use the functionality of this node in a child node
     you just have to create one function, which is _plotValues:
     
     **Parameters of `_plotValues`**

         :values:     dict  TimeSeries values, e.g.::

                           {'Standard': TimeSeries(...),'Target'  : TimeSeries(...)}

         :plot_label: str   Plot-Label
         :fig_num:    int   Figure-number for ?
         :store_dir:  str   Directory to store the plots
         :counter:    int   Plot counter for all trials
    
    Inside this function you can perform any plot you want.
     
"""
import os
import glob
import numpy
import warnings
import copy
import time

try:
    import pylab
    pylab_import_error=False
except:
    pylab_import_error=True

from collections import defaultdict
from pySPACE.missions.nodes.base_node import BaseNode
from pySPACE.tools.filesystem import create_directory

from pySPACE.missions.nodes.type_manipulation import type_conversion
from pySPACE.resources.data_types.prediction_vector import PredictionVector
from pySPACE.resources.data_types.feature_vector import FeatureVector
from pySPACE.resources.data_types.time_series import TimeSeries

class VisualizationBase(BaseNode):
    """ Base node for visualization
    
    If you want to use the functionality you can inherit from it, like, e.g.,
    ElectrodeCoordinationPlotNode does. See the module documentation for details.
    
    This base class provides the following functionality:

        - you can insert this node at any place in your node chain where the input data is a TimeSeries or a FeatureVector
        - you can optionally plot single trials and/or averages (the latter also accumulating over time)
        - you can either plot in online or in offline mode (see below)
        - data is sorted according to labels
        - optionally training and test data are distinguished
        - feature vectors are automatically transferred to time series
        - electrodes come with defined positions
       
    The node has a number of parameters to define what should be plotted, e.g.
    whether to plot single trials, accumulated average and/or average, or 
    to plot training vs test data, or to constrain to a certain label.
    
    Basically, there are two modes of plotting and storing the data: the
    offline mode (default) and the online mode. In the offline mode, the
    plotting is performed at the end and the plots are saved into the result_dir,
    specified for the store method in pySPACE. In the online mode, the plotting is
    performed as soon as the information is available and the user can specify
    the directory to store the data with the parameter user_dir.
          
    .. note::
      - Currently the data labels which are also given in the figure's title
        are based on the tag from the data.
      - If you use a splitter node previous to this node,
        the information of the different splits is also handled separately.
      - This node is not changing the data as such!
    
    .. note::
        Be careful when configuring matplotlib!
        Interactive matplotlib-backends are not compatible between offline and online, 
        when using live environment.
        Without the live environment, successful matplotlib backends
        used on a Mac were *Agg* (not interactive) and *MacOSX*. When using the live
        package, a working interactive matplotlib backend should be *GTKAgg*.
        You can change the matplotlib backend
        by modifying the *matplotlibrc* file in *.matplotlib* in
        your home directory, e.g. *backend : GTKAgg*.
    
   **Parameters**
   
    :General parameters:
    
        :rand_initial_fig:
            This option is useful when using the visualisation node multiple
            times within a node chain and getting the plots directly
            printed on-screen. The initial figure number is randomized between
            1 and 10000, so each visualisation node most likely plots into
            different figure windows.
            
            (*optional, default: True*)
    
        :online:
            The computation is performed in "online" mode, i.e. the plots are
            generated in the execution period of the node. If you additionally 
            store the data, the user_dir is used (see below).
            On the other hand, if the "offline" mode is used the plots are
            generated after all computations have been performed and the default
            way of saving the data is used.
        
            (*optional, default: False*)
        
    :Limit the amount of data:
    
        :limit2class:
            The string you specify here has to match the actual class label. 
            Then, only the data belonging to this class is
            plotted. 
        
            .. note:: If there is no match, no plot will be generated!
    
            (*optional, default: None*)
    
        :request_training:
            Has to be True if you want to plot data belonging to the training
            set. If you are only interested in test data, you can set this
            parameter to False.
        
            (*optional, default: True*)
    
        :request_test:
            Has to be True if you want to plot data belonging to the test set.
            
            (*optional, default: True*)
    
        :time_stamps:
            Specify which points in time should be included in visualization.
            With the default option, all available time stamps are displayed.
            The time_stamps are computed with respect to the timeshift option
            (see below), i.e. in a data window of 600 ms length, with
            timeshift = -200 and time_stamps = [200], the data at 400 ms in the
            original window is displayed.
        
            (*optional, default: [-1]*)
            
    :Influence the way how the data is plotted:
    
        :averaging:
            If this is true, all samples are averaged and the plot is created
            using this average. The average is performed with respect to the
            class labels.
        
            (*optional, default: True*)
        
        :accum_avg:
            If this is true, you will see the average accumulating with trials
            in a separate window. Again, this average is computed for each class
            separately.
        
            (*optional, default: False*)
        
        :single_trial:
            If this is true, single trials are plotted.
        
            (*optional, default: False*)
        
        :separate_training_and_test:
            When this option is True, training and test data are separately
            treated as if they belong to different classes. Therefore, if
            you have two original classes and set this option to True, 
            your plot will consist of four subplots. 
        
            .. note:: Setting this option
                to True will force request_training and request_test to True.
        
            (*optional, default: False*)
        
        :timeshift:
            This parameter shifts the labels of the time axis. If, e.g.,
            timeshift = -1000, the axis would show [-1000, 1000] instead of
            [0, 2000].
            Adjust this according to how the windowing was performed - usually
            one would want to have the marker at time 0.
    
            (*optional, default: 0*)
        
        :physiological_arrangement:
            This parameter
            controls whether the plots are arranged according to physiological
            positions. Otherwise this parameter has no effect.
            
            (*optional, default: True*)
        
    :Saving Options:
    
        :store:
            If this is true, the graphics are stored
            to the persistency directory at the end of the run.
        
            (*optional, default: False*)
        
        :user_dir:
            This option is only active, if plotting is in online mode
            (online=True) and store=True. Then the user can specify where the
            data should be stored.
            
            (*optional, default: './'*)
                    
        :create_movie:
            If this is True, a video of the average signals is created. Does
            require the ffmpeg library. The video is created from plots in the
            store_dir.
            
            .. note:: Enforces store=True.
    
            (*optional, default: False*)
    
        :store_data:
            With this additional option, you can store the data that has been
            used for plotting. The folder will be the same where the pictures
            are in. This option has no effect, if :store: is set to False.
        
            (*optional, default: False*)
                              
    :Author: Sirko Straube (sirko.straube@dfki.de)
    :Date of Last Revision: 2013/01/01
    """
    
    def __init__(self,
                 request_training=True,
                 request_test=True,
                 separate_training_and_test=False,
                 averaging=True,
                 accum_avg=False,
                 single_trial=False,
                 time_stamps=[-1],
                 store=False,
                 store_data=False,
                 create_movie=False,
                 timeshift=0,
                 online=False,
                 user_dir='./',
                 limit2class=None,
                 physiological_arrangement=True,
                 rand_initial_fig=True,
                 **kwargs):
        """ Used to initialize the environment.
           Called by VisualizationBase child-node.
           
           Parameters:    See description above.
           Returns:       Nothing.
        """
        
        #should training and test data be handled separately
        if separate_training_and_test:
            #if yes: all data has to be requested
            request_training = True
            request_test = True
            
        #modify request_training accordingly
        self.request_training = request_training

        super(VisualizationBase, self).__init__(store=store, **kwargs)
        
        if rand_initial_fig:
            initial_fig_num=int(numpy.random.rand()*10000)
        else:
            initial_fig_num=0

        if create_movie:
            #store the graphics to the persistency directory used in store_state
            store = True

        if not store:
            store_data = False

        #if plots are stored in online mode a directory is either specified or
        #data is stored in execution path
        if online and store:
            #is user_dir not set explicitly? 
            if user_dir == './':
                #set the user directory to the execution-path
                user_dir = '%s/' % os.getcwd()

            #add a folder with a timestamp
            user_dir = user_dir + time.strftime("%Y%m%d_%H_%M_%S") + \
                        '_Visualization_Plot/'
            
            create_directory(user_dir)
        else:
            user_dir = None #either offline plotting or store=False
        
        self.set_permanent_attributes(
            request_training=request_training,
            request_test=request_test,
            separate_training_and_test=separate_training_and_test,
            averaging=averaging,
            accum_avg=accum_avg,
            single_trial=single_trial,
            time_stamps=time_stamps,
            create_movie=create_movie,
            timeshift=timeshift,
            online=online,
            limit2class=limit2class,
            user_dir=user_dir,
            store_data=store_data,
            store=store,
            trial_counter=0,
            avg_values=dict(),
            accum_list=list(),
            st_list=list(),
            label_counter=defaultdict(int),
            skipped_trials=list(),  # list of not evaluated trials whenever
                                    # _execute was called
            physiological_arrangement=physiological_arrangement,
            initial_fig_num=initial_fig_num)
    
    def is_trainable(self):
        """ Returns whether this node is trainable.
            Method of base_node overwritten.
            
            Returns:       bool
        """
        return self.request_training
    
    def is_supervised(self):
        """ Returns whether this node requires supervised training.
            Method of base_node overwritten.
            
            Returns:       bool
        """
        return self.request_training
     
    def _train(self,
               data,    #TimeSeries, FeatureVector or PredictionVector
                        #      Data to work with.
               label):  #str   class label
        """ Every data instance that is passing this function 
            gets a flag.
            
            Returns:       nothing.
        """
        #notice that instance is training data
        data.specs['Training'] = True
     
    def _execute(self, data):  # data = pySPACE data instance
        """ This function performs a couple of operations:
            No matter what kind of data is arriving,
            the data is transformed into TimeSeries (for more information see below).  
            
            The main purpose of this function is to sort the data internally according
            to the applied and intended label (consisting maximally of "Training" or "Test"
            plus the actual class label) with respect to what should be plotted (single
            trial, average or accumulated average). In the end different the list of
            single_trials (st_list) and/or trials used for averaging (accum_list) are
            filled with respect to the evaluated label in this function.
            Accordingly separate counters are increased.
            
            These lists and counters can be easily used by any visualisation child node. 
        
            Data instance will be skipped, if
            o limit2class is set and the the current label of the data is different
            o we got training-data, but request_training is False
            o we got test-data, but request_test is False
            
            A list of skipped trials is built.
            
            If it has been set:
            The flag data.specs['Training']=True is evaluated and deleted afterwards.
            
            Two representations of the data can be computed:
            o single trial data (=data)
            o a running average (=accum_avg)

            In the online mode, the data is plotted here in the execute function
            (except average), otherwise in store_state.
                        
            Called by base_node.
            
            .. note::
                Currently the label is based on the tag. This should be fixed in the near future!
                
            Returns:       unmodified data
        """
        
        if pylab_import_error:
            warnings.warn("VisualizationBase::Pylab could not be imported. Plotting not supported.")
            return data

        #convert any datatype internally into TimeSeries
        #evaluate the datatype and prepare data accordingly
        dattype = type(data)
        if dattype == TimeSeries:
            # TimeSeries are used as they are
            prepared_data = data
        elif dattype == FeatureVector:
            # Feature Vectors are transformed into TimeSeries
            prepared_data = \
                type_conversion.FeatureVector2TimeSeriesNode()._execute(data)
        elif dattype == PredictionVector:
            warnings.warn("VisualizationBase:: Unsupported data type " + \
                              str(dattype) + "! Plotting ignored!")
            return data
        else:  # should never occur
            warnings.warn("VisualizationBase:: Unsupported data type " + \
                          str(dattype) + "! Plotting ignored!")
            return data

        #start...
        self.trial_counter += 1
        
        #get the label from the tag
        curr_label = data.tag.split()[-1]
        
        #training-data? 
        if data.specs.has_key('Training'):
            training_data = data.specs['Training']
            #in case splits are used, this information has to be deleted
            del data.specs['Training']
        else:
            #we are dealing with test data
            training_data = False
        
        if self.limit2class:
            # is the current label not the one the user is interested in?
            if curr_label != self.limit2class:
                #skip it
                self.skipped_trials.append(self.trial_counter)
                return data

        #distinguish between training and test data?
        if self.separate_training_and_test:
            if training_data:
                curr_label += '_Training'
            else:
                curr_label += '_Test'
                
        #do we have data that we not requested?
        elif (training_data and not self.request_training) \
                or (not training_data and not self.request_test):
            #skip it!
            self.skipped_trials.append(self.trial_counter)
            return data 
        
        #is averaging of the data intended?
        if self.averaging or self.accum_avg:
            #first time...
            if not curr_label in self.avg_values.keys():
                self.avg_values[curr_label] = prepared_data
                self.label_counter[curr_label] = 1
            #all other times...
            else:
                # collecting and updating list with respect to current label
                accumulated_value = \
                    self.avg_values[curr_label] \
                    * self.label_counter[curr_label] \
                    + prepared_data
                    
                self.label_counter[curr_label] += 1
                
                self.avg_values[curr_label] = \
                    accumulated_value / self.label_counter[curr_label]
                
            #plotting intended?
            if self.accum_avg:
                #store the data
                self.accum_list.append(copy.deepcopy(self.avg_values))
                #plots in online mode?
                if self.online:
                    #only possible if child has implemented the plot function
                    if hasattr(self, "_plotValues"):
                        self._plotValues(
                            values=self.avg_values,
                            plot_label="accum_avg_no_"+str(self.trial_counter),
                            fig_num=self.initial_fig_num+3,
                            store_dir=self.user_dir,
                            counter=self.trial_counter)
                    else:
                        warnings.warn("VisualizationBase:: The node you are using for visualisation " \
                                      "has no function _plotValues! This is most likely not what you intended!" \
                                      "Plotting ignored!")
        
        #single trials intended?
        if self.single_trial:
            #collect them...
            values = dict()
            values[curr_label] = prepared_data
            
            self.st_list.append(values)
            
            #plots in online mode?
            if self.online:
                #only possible if child has implemented the plot function
                if hasattr(self, "_plotValues"):
                    self._plotValues(
                        values=values,
                        plot_label="single_trial_no_"+str(self.trial_counter),
                        fig_num=self.initial_fig_num+2,
                        store_dir=self.user_dir,
                        counter=self.trial_counter)
                else:
                    warnings.warn("VisualizationBase:: The node you are using for visualisation " \
                                  "has no function _plotValues! This is most likely not what you intended!" \
                                  "Plotting ignored!")
        
        return data
    
    def store_state(self,
                    result_dir,     #string of results dir
                    index=None):    #None or int: number in node chain        
        """ Stores the plots to the *result_dir* and is used for offline
            plotting and for plotting of average values (online and offline).
            Plots offline-data for every trial which has not been skipped.
            Optionally creates movies based on the stored images.
            
            Called by base_node.
            
            Returns:       Nothing.
        """
        if self.store:
            #set the specific directory for this particular node
            node_dir = os.path.join(result_dir, self.__class__.__name__)
            #do we have an index-number?
            if index is None:
                #add the index-number...
                node_dir += "_%d" % int(index)
            create_directory(node_dir)
        else:
            #no specific directory
            node_dir=None
        #offline mode?
        if not self.online and (self.single_trial or self.accum_avg):
            if not hasattr(self, "_plotValues"):
                warnings.warn("VisualizationBase:: The node you are using for visualisation " \
                              "has no function _plotValues! This is most likely not what you intended!" \
                              "Plotting ignored!")
            else:
                pos = 0
                for trial_num in range(1, self.trial_counter+1):
                    if trial_num not in self.skipped_trials:
                        if self.single_trial:
                            self._plotValues(
                                values=self.st_list[pos],
                                plot_label="single_trial_no_" + str(trial_num),
                                fig_num=self.initial_fig_num+2,
                                store_dir=node_dir,
                                counter=trial_num)
                        if self.accum_avg:
                            self._plotValues(
                                values=self.accum_list[pos],
                                plot_label="accum_avg_no_"+str(trial_num),
                                fig_num=self.initial_fig_num+3,
                                store_dir=node_dir,
                                counter=trial_num)
                        pos += 1
            
        #plotting of the whole average or storage of the movie may also be possible in online mode
        if self.online:
            #set or change the the specific directory for the node to the
            #execution-path with a timestamp (see __init__)
            node_dir = self.user_dir
            
        #is averaging intended?
        if self.averaging:
            if not self.avg_values:
                warnings.warn("VisualizationBase:: One of your averages has no " \
                              "instances! Plotting ignored!")
            else:
                if hasattr(self, "_plotValues"):
                    self._plotValues(values=self.avg_values,
                                     plot_label="average",
                                     fig_num=self.initial_fig_num+1,
                                     store_dir=node_dir)
                else:
                    warnings.warn("VisualizationBase:: The node you are using for visualisation " \
                                  "has no function _plotValues! This is most likely not what you intended!" \
                                  "Plotting ignored!")
        
        #Finally create a movie if specified
        if self.create_movie and self.store_data:
            prefixes = []
            if self.single_trial:
                for trial in range(1, self.trial_counter+1):
                    prefixes.append("single_trial_no_" + str(trial))
            if self.accum_avg:
                for trial in range(1, self.trial_counter+1):
                    prefixes.append("accum_avg_no_" + str(trial))
            if self.averaging:
                prefixes.append('average')
            self._create_movie(prefixes=prefixes,
                               directory=node_dir)
        #close the figure windows
        pylab.close('all')
    
    def _create_movie(self,
                      prefixes,     #[str]  List of prefixes for the movies to create
                      directory):   #str    Directory for the node
        """ Creates movies based on the stored plots.

            Creates movies in the directory for the node. Movies will be created
            for those files with the given prefix. One movie for each prefix.
            Filename extensions may vary. See "man convert" for further
            informations.
            
            Returns:       Nothing.
        """

        #store current path
        former_dir = os.getcwd()
        
        #go to node dir 
        os.chdir(directory)
        
        for prefix in prefixes:
            counter = 0
            file_list = glob.glob("%s%s%s_*" % (directory, os.sep, prefix))
            
            if file_list != []:
                file_list = sorted(file_list) #note: check list sorting - there may still be a bug > leading zeros might still miss
                for file_str in file_list:
                    #convert format to temporary JPG and scale the image with x=2048
                    #save it in four-digit format
                    os.system("convert %s -resize 2048 %s%s%04d.jpg" % (file_str,
                                    directory, os.sep, counter))
                    counter += 1
                    #create an mp4-video-file with FPS=10, Bitrate=1800 based on the
                    #files in four-digit format
                os.system("ffmpeg -r 10 -b 1800 -i %04d.jpg " + str(prefix) +
                          ".mp4")
                
                #remove the temporary JPGs
                for c in range(counter):
                    os.remove("%04d.jpg" % c)
          
        #change dir back to old one
        os.chdir(former_dir)


#    def _get_electrode_coordinates(self, coordinates):
#        """ 
#        Convert the polar coordinates of the electrode positions
#        to cart of the physiologically
#        arranged plots. As the position specification also requires a height
#        and width, these values are also passed. Height and width are tuned
#        manually such that the resulting plots look nice. 
#        """
#        
#        # coordinate transformation
#        x = (coordinates[0] *
#             pylab.cos(coordinates[1] / 180 * pylab.pi) + 110) / 245
#        y = (coordinates[0] *
#             pylab.sin(coordinates[1] / 180 * pylab.pi) + 110) / 245
#        w = .07
#        h = .065
#    #        if self.shrink_plots:
#    #            w *= 1.2
#    #            h *= 0.9
#    #            x *= 4.0/3.0
#    #            y *= 4.0/3.0
#        
#        return [x, y, w, h]

