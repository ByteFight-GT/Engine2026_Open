## Getting Started

We recommend that if you are having trouble with installation, to watch our videos showing how to install. You can always contact devs on our Discord if you're still having trouble.

All of your code begins running starting from the `PlayerController` class in your `controller.py` file. We recommend you read the comments on your file to gain an initial understanding of the methods you will be required to implement.

To familiarize yourself with the game API, we recommend that you read the docs, which are  located in the scaffold at `docs/index.html`. We recommend you start with `game` (which gives a good first overall overview of the `game` package that you will use functions from).

When you're ready, head to [bytefight.org](https://bytefight.org/) and submit your code as a zip file via your team page.

We will be posting lectures from devs on topics including how to get started with ByteFight, data structures, algorithms, and optimizations among others.

## Competition Logistics
[This](https://acemagic.com/products/acemagic-w1-mini-pc?variant=49957899927858) is the computer that your code will run on. Your program is limited to 1.5GB of RAM, and 3 cores of CPU compute. All competition and ranked matches will be played on this computer. The code will be running on a securitized python3.12-slim docker environment with relevant packages installed.

However, in order to augment the speed at which we can process matches, we will also be using cloud compute to process scrimmages. While you will still have the same number of cores, the power of these cloud compute instances may be less powerful than the competition computer. Match results will be stamped with the CPU that was used to play the match and the version of the engine the match was played on. 

Your bots on your local client will be provided with double the amount of time to account for discrepancies between your computer and the competition environment, as well as no RAM limits.

You will have access to the python libraries `numpy`, `numba`, `torch`, and `cython`.`cython` will enable you to compile C, C++, and Rust binaries and run them via python bindings if you desire to do so. If you do submit these binaries, remember that they must be compiled for python3.12-slim, which can be done by downloading the docker container and/or using a vm. Extra python libraries may be provided on request, contact developers if there's a package you'd like included.
