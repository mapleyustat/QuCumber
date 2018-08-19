# Copyright 2018 PIQuIL - All Rights Reserved

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from .callback import Callback
from qucumber.observables import System


class ObservableEvaluator(Callback):
    """Evaluate and hold on to the results of the given observable(s).

    This Callback is called at the end of each epoch.

    .. note::
        Since Callbacks are given to :func:`fit<qucumber.nn_states.Wavefunction.fit>`
        as a list, they will be called in a deterministic order. It is
        therefore recommended that instances of
        :class:`ObservableEvaluator<ObservableEvaluator>` be the first callbacks in
        the list passed to :func:`fit<qucumber.rbm.nn_states.Wavefunction.fit>`,
        as one would often use it in conjunction with other callbacks like
        :class:`EarlyStopping<EarlyStopping>` which may depend on
        :class:`ObservableEvaluator<ObservableEvaluator>` having been called.

    :param period: Frequency with which the callback evaluates the given
                   observables(s).
    :type period: int
    :param \*observables: A list of Observables. Observable statistics are
                          evaluated by sampling the Wavefunction.
    :type \*observables: list(qucumber.observables.Observable)
    :param verbose: Whether to print metrics to stdout.
    :type verbose: bool
    :param \**sampling_kwargs: Keyword arguments to be passed to `Observable.statistics`.
                               Ex. `num_samples`, `num_chains`, `burn_in`, `steps`.
    """

    def __init__(self, period, *observables, verbose=False, **sampling_kwargs):
        self.period = period
        self.observables = observables
        self.observable_statistics = []
        self.system = System(*self.observables)
        self.last = {}
        self.verbose = verbose
        self.sampling_kwargs = sampling_kwargs

    def __len__(self):
        """Return the number of timesteps that observables have been evaluated for."""
        return len(self.metric_values)

    def clear_history(self):
        """Delete all statistics the instance is currently storing."""
        self.observable_statistics = []
        self.last = {}

    def get_value(self, name, index=None):
        """Retrieve the statistics of the desired observable from the given timestep.

        :param name: The name of the observable to retrieve.
        :type name: str
        :param index: The index/timestep from which to retrieve the observable.
                      Negative indices are supported. If None, will just get
                      the most recent value.
        :type index: int or None
        """
        index = index if index is not None else -1
        return self.observable_statistics[index][-1][name]

    def on_epoch_end(self, nn_state, epoch):
        if epoch % self.period == 0:
            obs_vals = self.system.measure(nn_state, **self.sampling_kwargs)

            self.last = obs_vals.copy()
            self.observable_statistics.append((epoch, obs_vals))

            if self.verbose is True:
                print("Epoch: {}\t".format(epoch), end="", flush=True)
                print(
                    "\t".join("{} = {:.6f}".format(k, v) for k, v in self.last.items())
                )
