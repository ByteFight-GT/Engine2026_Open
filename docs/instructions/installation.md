# Installation

**NOTE BEFORE BEGINNING:** The python terminal call used to run python files can vary between `py`, `python`, `python3`, and `python3.12` depending on OS and how your python installation is setup. When in doubt, try all of them.

## 1. Installing Python and a Virtual Environment manager

If you don't have python installed, download the [Python install manager](https://www.python.org/downloads/) and install **Python 3.12** (other versions will probably also work, but 3.12 is what we use on servers). Setting up this year's game will use a virtual environment manager: **venv** comes standard with python, but you may feel free to install and use other managers such as [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) or [conda](https://www.anaconda.com/download/success) if you want.

## 2. Creating the Environment
Download the [scaffold player_files.zip](https://drive.google.com/drive/folders/1TzzlKlM2wT8nvdzCBMrqZJGEs-V1wzsh) and extract it. Open a terminal in the folder you extracted it to. Then, create a virtual environment for Python 3.12 using the requirement.txt file from the scaffold.

If you are unsure of how to do so, read and follow the **Create and Use Virtual Environments**, **Prepare pip**, and **Using a requirements file** sections from this guide: [Creating a virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#using-a-requirements-file)

## 3. Running the game
Once you have created a virtual environment with the correct packages, you have two options, either to run the game - via our GUI client or via terminal.

### GUI Client
Download the relevant GUI client for your OS from the drive link on our website. 

After opening the client, go to the **settings** tab, click "set python executable location" and copy in the location of the python executable for your virtual environment. Some common places are listed below (where `<creation-directory>` in the directory where you created the environment and `<venv>` is the name of your virtual environment):

Note for apple to open the client, you will need to bypass security. Type this in your terminal.

xattr -dr com.apple.quarantine "Bytefight Client 2026.app"

**Windows venv**
```
<creation-directory>\<venv>\Scripts\python.exe
<creation-directory>\<venv>\Scripts\python.exe
```

**MAC/Linux venv**
```
<creation-directory>/<venv>/bin/python
<creation-directory>/<venv>/bin/python
```

**Windows conda**
```
C:\Users\<User>\miniconda3\envs\<venv>\python.exe
C:\Users\<User>\anaconda3\envs\<venv>\python.exe
```

**MAC/Linux conda**
```
/Users/<user>/miniconda3/envs/<venv>/bin/python
/Users/<user>/anaconda3/envs/<venv>/bin/python
/opt/miniconda3/envs/<venv>/bin/python
```


After setting the python path, all you need to go is go back to the game runner tab and
 - Set the directories of your two bots (they should be the directories containing `controller.py`) 
 - Set the map you want to play on
 - Begin the match!

### Terminal
Download the terminal distribution and extract it. Open a terminal in the folder that you extracted to. Then, activate the python environment you made in step 2. Every time you run the game you will need to have the python environment active.

Run the following command in terminal to run the game.

```
python engine/run_game.py --game_directory "arg1" --a_name "arg2" \
    --b_name "arg3" --map_name "arg4" --output_dir "arg5"
```

To find out what should go in each argument (and some extra arguments you can use to change how the game displays), run the following:

```
python engine/run_game.py --help
```

You may also instead elect to directly run from another script we provide without arguments. However, you will have to modify the `run_game_script.py` file to point to the correct workspace directory and agent folders programatically:

```
python engine/run_game_script.py
```

Feel free to modify run scripts as you'd like once you get more familiar with the competition.