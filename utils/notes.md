# Why Python

## Interpretable language
Language has to not use a compiler, no questions asked. A lot of intro CS people are barely going to be able to set up a Java or python environment, asking them to also compile the engine in order to play the game leads to a pretty high barrier to entry and lower reproducibility.

Best bytecode language options:
- Java
- Python
- C#
- JS
- Lua

Of these programming languages, most popular and well-known are Java, Python, and JS. We're not going to use JS because we definitely don't want to deal with the Node Package Manager.

## Java
### Performance
This is the one that people get really hung up about. At first glance it might seem that Java is the clear winner here (it runs much faster since it's compiled rather than interpreted like Python), and it seems suited to the task for distributed software(write once run anywhere), but upon closer inspection things aren't so clear-cut. 


## Python
Here I argue that Python is actually better despite its significant performance disadvantage. Java has a LOT of issues regarding the way that we want to run the competition. ByteFight is meant to be a lower barrier to entry, higher skill ceiling, more modern version of an AI competition compared to Battlecode. That means we want to allow students to do whatever they want within reason (and time limits). A-star and game tree searches, game acceleration, machine learning should all be on the table.

### OS Control
In order to allow for this high level of flexibility, we need A LOT of control over the operating system. Java simply doesn't have this: Battlecode does this through Bytecode checking, but we want to take a much more non-trivial question of how to run problematic, or even malicious code under time and memory constraints. This requires a much higher level of control over the OS (i.e. memory/VRAM checking, seccomp, user priveleges, and forced process termination). All of these items are significantly more difficult in Java than in Python. This brings me to the next point.

### Flexibility
While working within the tight constraints of Java is nice, it was originally designed as an enterprise-level easily-deployable language. Extending to anything outside of Java is non-trivial, and apparently the JNI is extremely confusing to use. Extending Java is still possible through the JNI, but is much more difficult and is not at all what Java is designed for. Compare this to Python, which has mature integration via Python bindings with C, C++, and Rust (which we currently support), and can even call into the JNI and .NET (C#) framework (which we currently don't). Python as a language was originally designed to overlay compiled code extraordinarily easily, which has made it a prime target for scientific computing and ML library support. This again leads me into my next point.

### Performance Mitigation
Python's performance issues can be largely mitigated by its stellar access to acceleration, whether it be through Python libraries like Numba and JAX or rewriting the engine in C, C++, or Rust. We may consider rewriting the engine in C as developers in the future, but I think that simply allowing competitors to do it may have some benefits. Writing the entire game in Python allows developers much easier maintainability and code comprehension compared to C-integrated Python. It also allows competitors to much more easily understand the game, which in turn allows them to more easily build their own simulations. Plus I think this is a unique thing about ByteFight that is not in the essence of Battlecode: acceleration of the game code by competitors, which I think is valuable in and of itself. Currently the plan is to have developers do a lecture on acceleration where we show how to accelerate the base game engine in Numba to show how it's possible.


## Final Mentions
A note to future developers regarding the use of wall clock time. It might seem weird at first given that we have access to CPU time but CPU time has issues with both ways of implementation
1. If we don't count child process time, you could just launch subtasks and sleep your main process, gaining essentially infinite resource computation time.
2. If we do count child process time, students lose access to the benefits of parallelization and multiprocessing, which is arguably one of the most important CS concepts to learn.

Using wall clock time solves both of these issues.

## Future Game Ideas
- Pacman: You control your team's players and ghosts
- Parallel: There's the "overworld" that uses regular movement mechanics and the "underworld" with modified mechanics. Actions in each world can affect the other. Either you have a mirror self that shadows your moves/can transfer between worlds/have 2 agents you control, working together to achieve an objective.
- Elevation: A 2.5d game where you have to reach a certain height/peak in order to win the game.
- Decryption: The game is centered around discovering secrets that can be used to decrypt either your opponent's or the game's secrets, giving you significant information/powerups/winning the game.