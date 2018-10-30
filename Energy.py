import os.path
import numpy as np
import matplotlib.pyplot as plt

from qucumber.nn_states import PositiveWavefunction
from qucumber.callbacks import MetricEvaluator
from qucumber.callbacks import ObservableEvaluator
from qucumber.callbacks import Timer
from qucumber.observables import Heisenberg1DEnergy

import qucumber.utils.training_statistics as ts
import qucumber.utils.data as data

def trainEnergy(numQubits,numSamples1 = "All",numSamples2 = 1000,burn_in = 100,steps = 100,mT = 60,trialNum = "Next"):
    '''
    Trains RBM on samples using energy observable as metric.

    :param numQubits: Number of qubits.
    :type numQubits: int
    :param numSamples1: Number of samples to use from training file.
                        Default is "All".
    :type numSamples1: int or "All"
    :param numSamples2: Number of samples to generate internally.
                        Default is 1000.
    :type numSamples2: int
    :param burn_in: Number of Gibbs steps to perform before recording
                    any samples. Default is 100.
    :type burn_in: int
    :param steps: Number of Gibbs steps to perform between each sample.
                  Default is 100.
    :type steps: int
    :param mT: Maximum time elapsed during training.
    :type mT: int or float
    :param trialNum: Trial number. Default is "Next".
    :type trialNum: int

    :returns: None
    '''

    # Load the data corresponding to the amplitudes and samples
    # of the quantum system
    psi_path = r"Samples/{0}Q/Amplitudes.txt".format(numQubits)
    train_path = r"Samples/{0}Q/Samples.txt".format(numQubits)
    train_data, true_psi = data.load_data(train_path, psi_path,
                                          numSamples=numSamples1)

    nv = train_data.shape[-1]
    nh = nv

    nn_state = PositiveWavefunction(num_visible=nv, num_hidden=nh)

    epochs = 1000
    pbs = 2
    nbs = 2
    lr = 0.001
    k = 1

    log_every = 1
    h1d_energy = Heisenberg1DEnergy()
    space = nn_state.generate_hilbert_space(nv)

    callbacks = [
        ObservableEvaluator(
            log_every,
            [h1d_energy],
            verbose=True,
            num_samples=numSamples2,
            burn_in=burn_in,
            steps=steps,
        ),
        MetricEvaluator(
            log_every,
            {"Fidelity": ts.fidelity},
            target_psi=true_psi,
            verbose=True,
            space=space
        ),
        Timer(mT,log_every,verbose = True)
    ]

    nn_state.fit(
        train_data,
        epochs=epochs,
        pos_batch_size=pbs,
        neg_batch_size=nbs,
        lr=lr,
        k=k,
        callbacks=callbacks,
    )

    energies = callbacks[0].Heisenberg1DEnergy.mean
    errors = callbacks[0].Heisenberg1DEnergy.std_error
    variance = callbacks[0].Heisenberg1DEnergy.variance

    epoch = np.arange(log_every, len(energies) + 1, log_every)
    epoch.astype(int)

    obsFile = open("Samples/{0}Q/Observables.txt".format(numQubits))
    obsFile.readline()
    line = obsFile.readline()
    H = round(float(line.strip("\n").split(" ")[1]),2)

    files = os.listdir("Data/Energy/Q{0}".format(numQubits))
    if trialNum == "Next":
        prevFile = files[-1]
        trial = 0
        for char in prevFile:
            if char.isdigit():
                trial = int(char) + 1

    ax = plt.axes()
    ax.plot(epoch, energies, color = "red")
    ax.set_xlim(left = 1)
    ax.axhline(H,color = "black")
    ax.fill_between(epoch, energies - errors, energies + errors, alpha = 0.2, color = "black")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Energy")
    ax.grid()
    plt.title("Samples = {0}".format(numSamples2) +
              " & Burn In = {0}".format(burn_in) +
              " & Steps = {0} for N = {1}".format(steps,numQubits))
    plt.tight_layout()
    plt.savefig("Data/Energy/Q{0}/Trial{1}".format(numQubits,trialNum))

    fidelities = callbacks[1].Fidelity
    runtimes = callbacks[2].epochTimes
    relativeErrors = []
    for i in range(len(energies)):
        relativeErrors.append(abs(energies[i] - H)/abs(H))

    resultsfile = open("Data/Energy/Q{0}/Trial{1}.txt".format(numQubits,trialNum),"w")
    resultsfile.write("samples: " + str(numSamples2) + "\n")
    resultsfile.write("burn_in: " + str(burn_in) + "\n")
    resultsfile.write("steps: " + str(steps) + "\n")
    resultsfile.write("Fidelities & ROE & RT & Mean & Variance & STD Error\n")
    for i in range(len(fidelities)):
        resultsfile.write(str(round(float(fidelities[i]),3)) + "  ")
        resultsfile.write(str(round(float(relativeErrors[i]),6)) + "  ")
        resultsfile.write(str(round(float(runtimes[i]),3)) + "  ")
        resultsfile.write(str(round(float(energies[i]),5)) + "  ")
        resultsfile.write(str(round(float(variance[i]),5)) + "  ")
        resultsfile.write(str(round(float(errors[i]),5)) + "  \n")
    resultsfile.close()

def analysis(numQubits):
    fidelities = []
    runtimes = []
    errors = []
    samples = []
    burn_in = []
    steps = []
    for i in range(1,28):
        trialfile = open("Data/Energy/Q{0}/Trial{1}.txt".format(numQubits,i))
        lines = trialfile.readlines()
        fidelitiesList = []
        runtimesList = []
        errorsList = []
        for j in range(len(lines)):
            if j == 0:
                samples.append(lines[j].strip("\n").split(" ")[1])
            elif j == 1:
                burn_in.append(lines[j].strip("\n").split(" ")[1])
            elif j == 2:
                steps.append(lines[j].strip("\n").split(" ")[1])
            elif j > 3:
                newline = lines[j].strip("\n").split(" ")
                fidelitiesList.append(float(newline[0]))
                errorsList.append(float(newline[2]))
                runtimesList.append(float(newline[4]))
        fidelities.append(fidelitiesList)
        runtimes.append(runtimesList)
        errors.append(errorsList)
        trialfile.close()

    runtime10 = []
    for i in range(len(runtimes)):
        runtime10.append(float(runtimes[i][10]))

    trials = list(range(1,28))
    plt.plot(trials,runtime10)
    plt.xlabel("Trial Number")
    plt.ylabel("RT for 10 Epochs")
    plt.savefig("Data/Energy/Q{0}/RTCompare".format(numQubits))

    for i in range(len(errors)):
        epochs = list(range(1,len(errors[i]) + 1))
        fig,axarr = plt.subplots(2,sharex = True)
        axarr[0].plot(epochs,fidelities[i])
        axarr[1].plot(epochs,errors[i])
        axarr[0].set_ylim(0.92,1)
        axarr[1].set_ylim(0,0.01)
        axarr[0].set_ylabel("Fidelity")
        axarr[1].set_ylabel("Relative H Error")
        axarr[0].set_title("Samples = {0}".format(samples[i]) +
                           " & Burn In = {0}".format(burn_in[i]) +
                           " & Steps = {0}".format(steps[i]))
        plt.xlabel("Epoch")
        plt.savefig("Data/Energy/Q{0}/Trial{1}".format(numQubits,i+1))
        plt.clf()
        plt.close()
