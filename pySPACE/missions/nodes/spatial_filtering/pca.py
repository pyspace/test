""" Principal Component Analysis variants """

import os
import cPickle

try:
    from mdp.nodes import PCANode
    from mdp.utils import mult
except:
    pass
from pySPACE.missions.nodes.spatial_filtering.spatial_filtering import SpatialFilteringNode

from pySPACE.resources.data_types.time_series import TimeSeries

from pySPACE.tools.filesystem import  create_directory
import logging
import numpy

class PCAWrapperNode(SpatialFilteringNode): #, PCANode):
    """ Reuse the  implementation of the Principal Component Analysis of mdp
    
    This node implements the unsupervised principal component
    analysis algorithm for spatial filtering.

    **Parameters**
        :retained_channels: Determines how many of the PCA pseudo channels
            are retained. Default is None which means "all channels".

        :load_path: An absolute path from which the PCA eigenmatrix
            is loaded.
            If not specified, this matrix is learned from the training data.

            (*optional, default: None*)

    **Exemplary Call**
    
    .. code-block:: yaml
    
        -
            node : PCA
            parameters:
                retained_channels : 42
    """
    def __init__(self, retained_channels=None, load_path=None, **kwargs):
        # Must be set before constructor of superclass is set
        self.trainable = (load_path == None)
        
        super(PCAWrapperNode, self).__init__(**kwargs)
        self.output_dim = retained_channels
        # Load patterns from file if requested
        if load_path != None:
            filter_file = open(load_path, 'r')
            avg, v = cPickle.load(filter_file)
            self.set_permanent_attributes(avg=avg, v=v, trainable=False, filters=v)
        
        self.set_permanent_attributes(# The number of channels that will be retained
                                retained_channels = retained_channels,
                                output_dim = retained_channels,
                                channel_names = None,
                                new_channels = None,
                                wrapped_node=None
                                )
        
    def is_trainable(self):
        """ Returns whether this node is trainable. """
        return self.trainable
        
    def is_supervised(self):
        """ Returns whether this node requires supervised training. """
        return False
    
    def _train(self, data, label = None):
        """ Updates the estimated covariance matrix based on *data*. """
        # We simply ignore the class label since we 
        # are doing unsupervised learning
        if self.wrapped_node is None:
            self.wrapped_node = PCANode()
        x=data.view(numpy.ndarray)
        self.wrapped_node.train(x)
        if self.channel_names is None:
            self.channel_names = data.channel_names
    
    def _stop_training(self, debug=False):
        """ Stops training by forwarding to super class. """
        self.wrapped_node.stop_training()
        #super(PCAWrapperNode, self)._stop_training(debug)
        self.v = self.wrapped_node.v
        self.avg = self.wrapped_node.avg
        self.filters = self.v
    
    def _execute(self, data, n = None):
        """ Execute learned transformation on *data*.
        
        Projects the given data to the axis of the most significant
        eigenvectors and returns the data in this lower-dimensional subspace.
        """
        # 'INITIALIZATION'
        if self.retained_channels==None:
            self.retained_channels = data.shape[1]
        if n is None:
            n = self.retained_channels
        if self.channel_names is None:
            self.channel_names = data.channel_names
        if len(self.channel_names)<self.retained_channels:
            self.retained_channels = len(self.channel_names)
            self._log("To many channels chosen for the retained channels! Replaced by maximum number.",level=logging.CRITICAL)
        if not(self.output_dim==self.retained_channels):
            # overwrite internal output_dim variable, since it is set wrong
            self._output_dim = self.retained_channels

        # 'Real' Processing
        #projected_data = super(PCANodeWrapper, self)._execute(data, n)
        x = data.view(numpy.ndarray)
        projected_data = mult(x-self.avg, self.v[:, :self.retained_channels])
        
        if self.new_channels is None:
            self.new_channel_names = ["pca%03d" % i 
                                for i in range(projected_data.shape[1])]
        return TimeSeries(projected_data, self.new_channel_names,
                          data.sampling_frequency, data.start_time,
                          data.end_time, data.name, data.marker_name)
        
    def store_state(self, result_dir, index=None):
        """ Stores this node in the given directory *result_dir*. """
        if self.store:
            node_dir = os.path.join(result_dir, self.__class__.__name__)
            create_directory(node_dir)
            # This node only stores the learned eigenvector and eigenvalues
            name = "%s_sp%s.pickle" % ("eigenmatrix", self.current_split)
            result_file = open(os.path.join(node_dir, name), "wb")
            result_file.write(cPickle.dumps((self.avg, self.v), protocol=2))
            result_file.close()


_NODE_MAPPING = {"PCA": PCAWrapperNode}
