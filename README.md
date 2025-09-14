# BunBunBash!

A real-world whack-a-mole style game using phone accelerometers as input devices.

## Inspiration

We wanted to make something fun. We spend lots of time on our phones and computers, but it's rare that those devices interact with the world; they're typically confined to a keyboard and a screen. We wanted a way to interact with music, games, websites, and all sorts of experiences with a simple setup based in the real world.

## What it does

Our setup involves a network of sensors using cell phone accelerometers. We detect peaks in acceleration to define a "hit," which can trigger any kind of event, including an event in a game or a simple keystroke. As a demo, we built a Whack-a-Mole-like game called Bun Bun Bash that takes input from real-world sensors to knock down bunnies. However, this setup is infinitely extendable; we used it to play the Chrome dinosaur game and online rhythm games, and we—or anyone else on Earth—can load custom JavaScript code to play any kind of game.

## How we built it

The accelerometer streams to a central web server via WebSockets. We then use our own peak detection algorithm to identify vibration-based signals, which produces a keyboard signal on the computer (e.g. hitting spacebar). The demo website and Bun Bun Bash are hosted on Flask and presented using HTML, with the game being built and run in JavaScript. Every icon, image, and background in the game was drawn and animated by hand.

## Individual Contributions

Peter worked on an early Arduino-based accelerometer prototype that evolved into phone sensors. Andromeda focused on getting accelerometer data using a website on each phone and feeding it to a central web server, where they wrote a custom peak detection algorithm and worked on analyzing the data and identifying signals. Xi wrote the graph data visualisation panel for calibration and debugging of incoming data signals, and used hand-drawn assets made by Jolie during the hackathon for the UI. Peter and Jolie built the demo website and Bun Bun Bash game from scratch, with Peter developing the backend and game functionality and Jolie crafting the user experience.

## Challenges we ran into

We originally wanted a lighter sensor based on an Arduino and an electronic accelerometer, but this was difficult to implement and would have only given us two sensors. We spent a long time working on getting data from phones to a computer with minimal latency, which eventually required creating a hotspot, running a local HTTPS server (we can't read accelerometer data in an insecure context), and connecting via WebSockets.. Raw data is inherently very noisy and hard to interpret, which made peak detection and separation difficult but not impossible. Finally, it was hard to create a satisfying game that works well with the slight latency we have.

## Accomplishments that we're proud of

We're very proud that our sensors work as well as they do on various surfaces—tables, chairs, arms, you name it. It operates under extreme hardware limitations; usually piezo/accelerometer sensors for vibration detection run at >=1000Hz, but mobile phones provide ~40Hz of extremely noisy data. It's also not at all attached to our physical hardware, making it very easy for others to replicate with a bit of scaffolding. We're also very happy with the game we've created, and we have very much accomplished our goal of building a fun real-world game.

## What we learned

We solved a problem unique to our environment, which was finding the best kind of vibration sensors. We learned how to communicate with built-in iPhone data and found it to be easier than we expected, making a custom sensor unnecessary. We also learned better practices for maintaining streamlined communication and documentation.

## What's next for our project

Essentially, we want to make it easier to expand this to new environments. We'd love to make our phone protocol simpler and less dependent on network/hotspot connection, which we needed to reduce latency. We'd also love to make a website that can host any game and allow users to upload their own games, which they can then play on their own phones in whatever environment they're in.
