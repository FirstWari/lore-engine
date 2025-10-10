# Advanced 2. Semantic Localization (720P30) - Part 1

![Screenshot at 00:00:00](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-00-00.jpg)

# 16.412 Cognitive Robotics - Advanced Lecture 2: Semantic Localization (Spring 2016)

## Introduction to Semantic Localization

This lecture will cover:
*   What semantic localization is and its motivations.
*   An algorithm for localization.
*   How to integrate semantic information into this algorithm.

## Motivation: The Orienteering Grand Challenge Analogy

The concept of semantic localization is inspired by challenges like orienteering.

### What is Orienteering?
*   Participants are given a map and a compass.
*   The goal is to navigate to various checkpoints.
*   It's challenging because participants don't precisely know their location on the map, relying only on the compass and visual cues.

### Human Strategies for Localization (Orienteering Experts)
When disoriented, humans employ several strategies:
1.  **Find a Reference Point:** Identify a unique, known landmark to re-establish position.
2.  **Estimate Movement:** Recall the last known location and estimate movement since then to narrow down possible current positions.
3.  **Identify Unique Features:** Look for distinct features on the map that can be uniquely identified in the environment.

![Screenshot at 00:01:01](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-01-01.jpg)

*   An orienteering map (as shown above) is not useful on its own. For instance, patches of green might be guessed as grass, but their specific meaning is unknown.
*   A **legend** is crucial: It defines symbols for roads, footpaths, pits, and other features, making the map interpretable and usable for navigation.

### Human vs. Robot Localization

There's a fundamental difference in how humans and traditional robots localize:

| Feature           | Human Localization                                  | Traditional Robot Localization                            |
| :---------------- | :-------------------------------------------------- | :-------------------------------------------------------- |
| **Perception**    | Focus on abstractions (e.g., "rooms," "kitchens")   | Measures precise distances (e.g., with laser scanners)    |
| **Information**   | Understands purpose and relative locations of objects | Forms a perfect, metric map of the entire space           |
| **Interpretation**| Uses signs and symbols with meaningful concepts     | Relies on raw sensor data and geometric representations   |

## Defining Semantic Information

![Screenshot at 00:02:50](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-02-50.jpg)

*   **Definition:** Semantic information refers to "signs and symbols that contain meaningful concepts for humans."
*   In essence, it involves using **abstractions** that humans naturally understand and utilize for navigation and interaction.

## Why Semantic Information is Important

![Screenshot at 00:03:39](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-03-39.jpg)

Semantic information offers significant advantages for robotic systems:

1.  **Improved Human-Robot Interaction:**
    *   Enables robots to understand and execute commands given in human language (e.g., "go to the kitchen," "get a mug," "turn on the coffee maker").
    *   Requires the robot to understand what objects are (e.g., "coffee maker"), their function, and their location.
    *   This facilitates a more natural and intuitive interaction paradigm.

2.  **Performance and Memory Optimization:**
    *   **Reduced Map Size:** Robots don't need to store a full, highly detailed metric map of every surface and distance. Instead, they store locations of key semantic information (e.g., "kitchen," "coffee maker").
    *   **Smaller Search Space:** Localization and navigation algorithms can prune irrelevant areas. For example, if a robot needs to find a coffee maker, it can focus its search only within areas identified as "kitchens," significantly reducing the computational load.

3.  **Cheaper and More Accessible Hardware:**
    *   Semantic localization can often be achieved using simpler sensors, such as a camera, rather than expensive and complex laser scanners or Lidar systems.
    *   This makes robotic systems more affordable and widely accessible.

---

## Defining Semantic Localization

![Screenshot at 00:04:04](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-04-04.jpg)

*   **Semantic localization** is the process of localizing a robot based on **semantic information** rather than traditional **metric information** (e.g., precise distances and angles).
*   **Context for the Grand Challenge:**
    *   A map is provided, which contains labeled objects and their corresponding coordinates.
    *   The robot observes its surroundings (what objects are in its field of view).
    *   The objective is to determine the robot's probable location on the map based on these observations.
*   **Important Distinction:** This problem assumes a pre-existing map. **Map building** is a separate, complex area of research not addressed here. The focus is purely on localization using a given map.

## Particle Filters for Localization

Matt Dio explains particle filters as an algorithm for state estimation, specifically for localization, using a given map and measurements.

### What is Localization?
*   Localization addresses the fundamental question: "Where am I?"
*   For any autonomous system to function effectively, it must know its position on a map.

### Metric Localization (Traditional Approach)
*   **Quantitative:** Defines position using numerical values, such as:
    *   Distance from a wall or origin (e.g., "5 meters from this wall").
    *   Orientation in degrees (e.g., "oriented at 45 degrees").
*   Facilitates easy conversion between different coordinate frames.

### Mathematical Problem Statement for Localization
Localization, in a mathematical context, involves probabilistic state estimation:
*   **Inputs:**
    *   `u` (control command): The action the robot takes (e.g., move forward, turn).
    *   `z` (observation): Sensor data collected from the environment (e.g., camera images, laser scans).
    *   `Map`: A representation of the environment.
*   **Goal:** To determine the probability of being at a certain position at the current time, `P(position_t | position_{t-1}, z_t, u_t, Map)`.
*   This probability is influenced by:
    *   **Observation Noise:** Imperfections in sensor readings.
    *   **Actuation Noise:** Inaccuracies in robot movement based on control commands.
    *   **Belief:** The robot's current estimate of its state.
*   Particle filters specifically focus on refining this "belief."

### Particle Filter Demo Example

![Screenshot at 00:06:53](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-06-53.jpg)

A YouTube demo illustrates a particle filter in action for an autonomous robot navigating a maze.

#### Initial State
*   **Robot Position:** Represented by a red dot (the actual position).
*   **Environment:** A maze with black walls, appearing as a grid world.
*   **Initial Particle Distribution:** The blue dots represent particles, which are random guesses of the robot's position. Initially, these particles are distributed randomly across all possible locations in the maze, including walls.

![Screenshot at 00:07:16](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-07-16.jpg)

#### Observation and Belief Update
*   **Observations:** The robot takes observations, likely from laser range finders. These observations provide information about the presence or absence of walls (e.g., "there are walls around me," "there is no wall in front of me").
*   **Particle Resampling/Weighting:**
    *   Particles that contradict the observations (e.g., particles located inside a wall or in open space where a wall is detected) are assigned very low probabilities or eliminated.
    *   This process effectively "centers" the remaining particles (guesses) in areas consistent with the observations, such as the middle of hallways.
    *   The image above shows particles (blue dots) clustering in open areas, away from walls, as their probability of being near a wall is low given the sensor readings.

---

### Particle Filter Steps

The particle filter method involves four key steps:

1.  **Initialization (Once):** Sample initial particles to represent the robot's belief about its state. If the initial state is unknown, particles can be sampled uniformly across the entire possible state space.
2.  **Repeated Steps:**
    *   **Update Weights:** Adjust the probability (weight) of each particle based on new observations.
    *   **Resampling:** Create a new set of particles by drawing from the current set, with higher-weighted particles being more likely to be selected. This maintains a constant number of particles.
    *   **Propagate with Dynamics:** Move each particle according to the robot's motion model and its associated noise.

## Toy Example: Aircraft Localization

To illustrate the particle filter, a simplified one-dimensional example is used: localizing an aircraft.

### Scenario Setup
![Screenshot at 00:08:27](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-08-27.jpg)

*   **Aircraft:**
    *   Flies at a **constant altitude**.
    *   **Unknown X location** (horizontal position) along a map. This is the variable to be localized.
    *   Has a **noisy forward velocity** (known nominal velocity, but with some uncertainty).
*   **Sensor:**
    *   A **range finder** pointing downwards to the ground.
    *   Measures the **distance to the ground below**.
    *   Provides **noisy measurements**.
*   **Map:**
    *   A **known mapping of X location to ground altitude**. This means for any X coordinate, the terrain height is known.
    *   Visually represented as a mountain range.

### Goal
*   Determine the aircraft's unknown state, specifically its X location, within the mountain environment.

### Detailed Explanation of the Setup
![Screenshot at 00:08:36](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-08-36.jpg)

*   The aircraft maintains a constant altitude.
*   The map below shows varying ground altitudes (mountains).
*   The range finder measures the depth from the constant altitude down to the ground.
    *   A long distance indicates the aircraft is over a valley.
    *   A medium distance indicates it's over a slope.
    *   A short distance indicates it's directly over a mountain peak.
*   The aircraft's X position is unknown.
*   The forward velocity has noise, meaning the actual movement might be slightly faster or slower than commanded.

### Step 1: Sampling (Initialization)

*   **Initial Belief:** Assuming no prior knowledge of the aircraft's X location.
*   **Method:** Particles are sampled from a **uniform distribution** across the entire possible range of X locations on the map.
*   These particles represent initial guesses for the aircraft's X coordinate.

### Step 2: Update Weights (Based on Observation)

![Screenshot at 00:09:58](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-09-58.jpg)

*   **Observation:** The range finder provides a first measurement (e.g., a "long" distance, indicated by green in the example).
*   **Expected Values:** For each particle (each guess of X location), the expected range finder measurement can be calculated using the known map (i.e., the distance from the constant altitude to the ground at that particle's X location).
*   **Weight Calculation:**
    *   The likelihood of observing the actual measurement (e.g., "long distance") is calculated for each particle's expected measurement.
    *   Particles whose expected range finder measurements closely match the actual observed measurement receive **higher weights**.
    *   Particles whose expected measurements deviate significantly from the observation (e.g., particles over a mountain peak if a long distance was observed) receive **smaller weights**.
    *   This process effectively assigns a probability to each particle based on how well it explains the current sensor reading.

### Step 3: Resampling

*   **Purpose:** To maintain a constant number of particles while focusing the distribution on more likely states.
*   **Method:** New particles are drawn from the current set of particles. The probability of drawing a particular particle is proportional to its weight.
*   This means particles with higher weights (representing more likely locations) will be "cloned" more often, while low-weight particles are more likely to be discarded. The total number of particles remains the same, but their distribution shifts towards more probable areas.

---

### Step 4: Propagating with Dynamics

*   **Concept:** While observations are taken and weights are updated, the robot (aircraft in this example) is continuously moving. This movement must be accounted for.
*   **Method:**
    *   Each of the newly resampled particles is moved forward according to the robot's dynamics model (e.g., forward velocity).
    *   **Uncertainty:** The propagation step incorporates noise in the robot's movement. For example, if the aircraft has a noisy forward velocity, each particle will move by a slightly different amount, sampled from a distribution around the expected movement. This means some particles might move a bit faster or slower than the average.
    *   This generates new particles for the next iteration, reflecting the robot's estimated movement.

### Iterative Process and Convergence

The particle filter continuously repeats steps 1 (Update Weights), 2 (Resample), and 3 (Propagate) as new observations come in.

*   **Initial State:** Many particles are spread out, representing high uncertainty.
*   **First Observation:** Particles inconsistent with the observation are down-weighted or removed, and remaining particles are resampled. This starts to cluster particles in areas that match the observation (e.g., "long distance" means particles are likely over valleys).
    *   ![Screenshot at 00:10:54](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-10-54.jpg) (Implied state after initial resampling, showing particles clustered in valleys)
*   **Subsequent Observations and Movement:** As the aircraft moves and takes more measurements, the particle distribution becomes increasingly refined.
    *   For example, if the next observation indicates "halfway up the mountain," particles that align with this new reading (e.g., on slopes) gain weight, while others diminish.
    *   As the aircraft moves over a mountain peak, particles will cluster over peaks.
    *   Eventually, a unique sequence of observations and movements will allow the filter to differentiate between previously ambiguous locations.
    *   For instance, if two mountain peaks look similar, but one is followed by a much deeper valley than the other, the distinct "drop-off" measurement will eliminate particles from the incorrect peak.
*   **Convergence:** The goal is for the particle distribution to converge to a small cluster, indicating a high probability of the robot being in a specific location.

### Re-visiting the Localization Demo

![Screenshot at 00:12:12](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-12-12.jpg)

The maze localization demo (from earlier) is reviewed with the understanding of particle filter steps:

*   **Initial Distribution:** The robot starts with a uniform distribution of particles, signifying complete uncertainty about its position in the maze.
*   **First Observations (Walls):** The robot's laser rangefinders detect walls. Particles that are inside walls or in open spaces where walls are detected are down-weighted. This causes particles to cluster in hallways and open areas, away from walls.
*   **Movement and Further Observations:** As the robot moves and observes changes in its environment (e.g., seeing a doorway to the left), the particle filter continues to update weights and resample.
*   **Eliminating Ambiguity:**
    *   Initially, the robot might know it's in a long hallway but not its orientation (e.g., facing left or right, or at which end of the hallway).
    *   As it moves further (e.g., two blocks) without encountering a wall directly in front or a turn-off, this unique geometric sequence helps eliminate all but a few possible locations.
    *   The particles eventually converge to the correct location and orientation, as the observed sequence of geometric features becomes unique to a single spot on the map.

---

### Localization Demo Conclusion

*   The particle filter successfully localized the robot in the maze.
*   By continuously processing observations (walls, doorways) and propagating particles based on movement, the filter eliminated ambiguous states.
*   Eventually, the unique geometry of the environment allowed the particles to converge to a single, correct location and orientation for the robot. This demonstrates the effectiveness of particle filters for metric localization using range finders.

## Implementing Semantic Localization

David Stingley now elaborates on how to combine the concept of semantic localization with particle filters to implement it on a robot.

### Key Components of Localization

Regardless of whether it's metric or semantic, any localization system requires three core components:

1.  **Belief Representation:** How the robot represents its uncertainty about its current location. Particle filters provide this by maintaining a distribution of possible states (particles).
2.  **Actuation Model:** Describes how the robot moves and the uncertainty associated with that movement.
    *   This includes the probability of moving to various locations given a control command (`P(X_{t+1} | X_t, U_t)`), accounting for noisy velocity or other dynamics.
3.  **Observation Model:** Defines the probability of observing a certain sensor reading given the robot's current position.
    *   This is the core of how the robot interprets sensor data to update its belief (`P(Z_{t+1} | X_{t+1})`).

*   By continuously solving for the most probable particle (or the mean/mode of the particle distribution), the system determines the robot's estimated location.

### Pseudocode for Semantic Localization

![Screenshot at 00:16:07](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-16-07.jpg)

The process of semantic localization using a particle filter can be outlined as follows:

```
While the robot is moving:
    1. Make observations (Z_t+1)
    2. Generate probable locations (P(X))
       *   Start/initialize particle filter.
       *   Guess a certain number of probable locations (particles).
    3. Update that location based on actuation (P(X_t+1 | X_t, U_t))
       *   Propagate particles forward based on the robot's motion model and uncertainty.
    4. Simulate observations at that location (P(Z_t+1 | X_t+1))
       *   For each particle's simulated position, predict what observations would be seen on the map.
    5. Compare expected and actual observations
       *   Compare the simulated observations (from step 4) with the actual observations (from step 1).
    6. Update our location estimates based on comparison
       *   Update the weights of the particles based on this comparison (how well each particle's predicted observation matches the real one).
       *   Resample particles.
```

*   **Focus on the Observation Model:** A significant part of this process (steps 4 and 5) involves defining and using the observation model (`P(Z_{t+1} | X_{t+1})`). This is where semantic information is integrated.

### Observation Model Selection

![Screenshot at 00:16:16](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-16-16.jpg)

The choice of observation model (`z`) is critical for semantic localization. Different models have varying requirements for information and complexity:

1.  **A Labeled Laser Scan (Metric Localization):**
    *   In traditional metric localization, laser scanners provide precise distance information.
    *   If combined with object detection, it could yield "perfect information" about the environment (e.g., a wall at 3 meters, a door at 5 meters).
    *   This approach is highly data-intensive and computationally demanding.

2.  **A Scene with Objects at Specific Locations:**
    *   This involves knowing the exact locations and orientations of objects relative to each other within the scene.
    *   Requires a rich, detailed map that specifies object poses.
    *   Still quite information-heavy.

3.  **A Set of Objects (Bag of Objects):**
    *   This is a simpler, more abstract representation.
    *   The observation might be a count or list of detected objects without precise spatial relationships (e.g., "I see four chairs," "I see a table and three chairs").
    *   This model reduces the amount of information needed, simplifying the localization problem.

The complexity of the observation model directly impacts the required sensor data, map detail, and computational resources. Using simpler, more abstract representations (like a bag of objects) is often preferred in semantic localization to reduce complexity.

#### Example: Complexity with Laser Scanners and Objects
Consider using laser scanners with semantic objects like a house, trees, and a mailbox.
*   Each laser line would need to be checked for intersections with these objects.
*   This quickly becomes very complex due to the need for precise geometric models of objects and their interactions with laser beams.

---

### Challenges in Defining "Detection"

![Screenshot at 00:17:10](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-17-10.jpg)

*   When using laser scanners with objects, defining what constitutes a "detection" is complex.
*   The system must differentiate between various objects within its field of view.
*   For example, if a large wall is scanned, how does the system know where a "house" begins or ends within that wall?

### Object-Point Assumption

![Screenshot at 00:17:30](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-17-30.jpg)

To simplify detection, one might assume objects are represented as points:
*   **Assumption:** An object is either entirely visible or entirely not visible.
*   **Detection Method:** Check if the object's "center of mass" (or a specific point representing it) intersects with the robot's current view plane.
*   **Issue:** This approach is overly simplistic. If an object's center point is outside the view plane, even if parts of the object are visible, the object is completely ignored. This leads to information loss.

### More Complex Object Models

*   More sophisticated models could involve representing objects as **polygons** or considering **parts of objects**.
*   This introduces questions like: "Do you see some percentage of something?" or "How much of it is in the view plane?"
*   While more accurate, these models significantly increase complexity and the potential for errors.

### New Observation Types Mean New Error Types

![Screenshot at 00:18:09](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-18-09.jpg)

The way observations are characterized directly influences the types of errors that can occur:

| Observation Type       | Potential Errors                                                                                                              |
| :--------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| **Distance & Bearing** | **Noise:** Inherent inaccuracies in sensor readings. <br> **Sensor Limitations:** Inability to see objects beyond a certain range or if they are rotated unfavorably. |
| **Object Class**       | **Classification Error:** Misidentifying an object (e.g., mistaking a large mailbox for a small tree or vice-versa).           |
| **Sets of Objects**    | **Equality under Permutations:** If the relative order or position of objects within a set is not considered, `[tree, tree, mailbox]` might be indistinguishable from `[mailbox, tree, tree]`. This prevents unique scene identification based on object arrangement. |

### Refining the Observation Model for Semantic Localization

![Screenshot at 00:19:17](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-19-17.jpg)

The probability statement for the observation model `P(Z_{t+1} | X_{t+1})` needs to be made more concrete for semantic localization.

*   **Revised Notation:** `P(Z | Y(x), x)`
    *   `Z`: The **set of observed objects** (e.g., `Z = {house, mailbox}`). This is the actual sensor input.
    *   `Y(x)`: The **set of objects you would see** if you were at position `x`. This is the prediction based on the map and the particle's hypothetical position.
    *   `x`: The robot's current **position** (derived from a particle filter's estimate).

*   **"Bag of Objects" Approximation:** This approach simplifies the observation model by treating `Z` and `Y(x)` as unordered collections of objects. This means the relative positions or orientations of objects within the scene are not explicitly considered, only their presence.

### Example Scenario: Trees and Mailboxes

*   **Map:** A long road with trees and mailboxes positioned along its sides.
*   **Objects:** Trees and mailboxes are chosen as the semantic objects for this example.
*   **Process:** The robot will observe a set of trees and mailboxes (`Z`) and compare it to the set of trees and mailboxes it *would* see from a hypothetical position `x` (`Y(x)`), to determine the likelihood of `x` being the true position.

---

### Example Scenario: Robot as a Paper Delivery Boy

![Screenshot at 00:20:26](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-20-26.jpg)

*   **Robot's Goal:** Deliver papers, requiring localization of mailboxes and its position on the street.
*   **Environment:** A road with trees (green blobs) and mailboxes (blue squares).
*   **Robot's Representation:** An orange hexagon with a defined field of view (FoV).

#### Actual Observation (Z)

*   From the robot's actual position and FoV, it sees: **one tree and one mailbox**.
*   **Simplifying Assumption:** For the purpose of this example, it's assumed that if any part of an object intersects the FoV, the object is fully seen. So, both trees and the mailbox are considered "seen."

#### Synthetic Observations (Y(x))

*   When the particle filter spawns particles (hypothetical positions `x`), the system needs to determine what `Y(x)` (the set of objects seen from that hypothetical position) would be.
*   For example, if a particle is spawned slightly further forward (deviated from the actual position), the set of objects `Y(x)` might be different.
*   Calculating `P(Z | Y(x), x)` critically depends on accurately determining `Y(x)` for each particle.

## Key Considerations for Observation Models

![Screenshot at 00:21:54](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-21-54.jpg)

When developing the observation model for semantic localization, several types of errors and complexities need to be considered:

1.  **Classification Errors:**
    *   Did the robot correctly classify the observed objects?
    *   (e.g., Mistaking a tree for a mailbox, or vice-versa).
    *   This is crucial for the "set of objects" approximation, where object identity is key.

2.  **Missing Observations:**
    *   Did the robot observe everything within its Field of View (FoV)?
    *   (e.g., A tree might intersect the FoV but not be detected due to occlusion or sensor limitations).

3.  **Spurious Detections (False Positives):**
    *   Did the robot interpret "nothing" as "something"?
    *   (e.g., Detecting a tree when there isn't one, due to sensor noise or misinterpretation).

4.  **Overlapping Objects (Ambiguity):**
    *   Did the robot interpret two things as one thing?
    *   (e.g., Two trees positioned very close together might be perceived as a single, larger tree). This makes it difficult to count individual objects accurately.

### Key Assumption 1: One Observation = One Object

To simplify the problem, a critical assumption is made:
*   **Assumption:** Every observation corresponds to exactly one object being seen.
*   **Rationale:** Without this assumption, the problem can become infinitely complex. If one observed tree could potentially be two trees, and each of those two could be two more, the scene could recursively expand, making probability calculations intractable and preventing the algorithm from converging.
*   By making this assumption, the system avoids this combinatorial explosion, ensuring that the algorithm can finish its calculations. This simplifies the error model to focus on misclassification or missed/spurious detections rather than object multiplicity ambiguity.

The next step is to address whether objects are classified correctly.

---

## Addressing Classification Errors in Semantic Localization

The next challenge is to determine the probability that the robot's classification of observed objects is correct.

### Simplifying Assumptions for Observation Model

To make the problem tractable, two initial simplifying assumptions are made (which will be relaxed later):

1.  **No Missed Detections:** We assume the robot sees **everything** inside its Field of View (FoV). This eliminates the problem of "Did we observe everything in our FoV?"
2.  **No False Detections:** We assume the robot **never sees something that doesn't exist**. This eliminates the problem of "Did we interpret nothing as something?"

*   **Result:** Under these assumptions, everything that is truly in the scene and within the FoV is seen, and nothing extra is detected.

### Example: Robot Observation and Synthetic Prediction

![Screenshot at 00:23:23](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-23-23.jpg)

Consider a robot at a position with a certain FoV.

*   **Actual Observation (Z):** The robot's sensors detect **one mailbox and two trees**.
*   **Synthetic Prediction (Y):** From a *hypothetical* particle position, the map indicates that the robot *should* see **three trees**.

The task is to reconcile `Z` (actual observation) with `Y` (synthetic prediction).

#### Reconciling Z and Y

![Screenshot at 00:24:11](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-24-11.jpg)

*   To transform `Y` (three trees) into `Z` (one mailbox, two trees), a **misclassification** must have occurred.
*   Specifically, one of the three trees in `Y` must have been misclassified as a mailbox to match `Z`.
*   Since `Z` and `Y` are treated as **sets of objects (bag of objects)**, the specific identity of *which* tree was misclassified doesn't matter. Any one of the three trees could have been the one misclassified as a mailbox.

#### The Permutation Operator `Pi`

![Screenshot at 00:24:49](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-24-49.jpg)

*   To account for all possible permutations of misclassifications, a concept called the **permutation operator `Pi`** is introduced.
*   `Pi` (represented as `Pi = {Z <-> Y}`) maps the expected synthetic observation `Y` to the actual observation `Z` by considering all possible ways misclassifications could have occurred.
*   This operator can be conceptually thought of as a permutation matrix that reorders and potentially changes the type of elements to match the observed set.

### Probability Calculation: `P(Z | Y(x), x)`

Now, let's refine the probability statement `P(Z | Y(x), x)`:

*   We use `z`, `y`, and `i` to represent individual elements (objects) within the sets `Z` and `Y`.
*   The core of the calculation is determining the probability that an element `y` from our synthetic observation `Y(x)` matches an element `z` from our actual observation `Z`.

#### Factors Influencing Probability

1.  **Classification Matrix (C):**
    *   This matrix defines the probability of correctly classifying an object or misclassifying it as another type of object.
    *   `P(observed_type | true_type)`
    *   Typically, the probability of correct classification is high, while the probability of misclassification (e.g., a tree being seen as a mailbox) is low.

2.  **Weighted Classification Confidence:**
    *   Modern classification systems (e.g., neural networks) often output a **confidence score** along with a classification.
    *   This confidence can be incorporated into the probability calculation. For example, `P(Z | Y(x), x)` could include a term that represents "what is the probability that the classification score indicates this type of object?"
    *   Higher confidence in a correct classification would increase the overall likelihood.

3.  **Contextual Factors / Sensor View:**
    *   The probability of correct classification might also depend on the object's **orientation** or other contextual information relative to the sensor.
    *   (e.g., A classification engine might be much better at identifying a mailbox from the front view compared to a side view). This information can be integrated into the observation model to further refine the probability.

---

### Comprehensive Probability for Classification

![Screenshot at 00:26:35](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-26-35.jpg)

The probability of an individual observed element `z_i` matching a synthetic element `y_i` given position `x`, `P(z_i | y_i, x)`, can be broken down into multiple terms:

*   `P(c | y_i^class)`: **Classification accuracy.** How often `y_i` (true class) is correctly classified as `c` (observed class). This is represented by the classification matrix `C`.
*   `P(s | c, y_i^class)`: **Statistical likelihood of classification score.** If the classification system provides a score (e.g., from a neural network), this term represents the probability that the score `s` is observed, given the true class `y_i^class` and the observed class `c`. This incorporates the confidence of the classifier.
*   `P(b | y_i, x)`: **Effect of bearing/orientation.** This term accounts for how the robot's viewing angle (`b`) of object `y_i` (at position `x`) affects the classification probability. For instance, a mailbox might be easier to identify from the front than from the side.

*   **General Principle:** The more specific the classification information (e.g., including confidence, orientation), the more terms can be introduced into the probability model. This helps to reduce misclassification probabilities and make the model more robust.

### Overall Probability for Sets

The overall probability `P(Z | Y(x), x)` for entire sets of objects is calculated as a product over all possible classifications for a selection of permutations.
*   It considers all permutations between the elements of the observed set `Z` and the synthetic set `Y(x)`.
*   For each permutation, the individual probabilities of classifying each object correctly (or incorrectly) are multiplied together. This yields the total probability of observing set `Z` given that the robot is at position `x` and expects to see set `Y(x)`.

## Relaxing Assumptions: "Did We See Everything?"

The previous assumption that "we see everything in our FoV" is now relaxed to address missed detections.

### New Scenario

![Screenshot at 00:27:47](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-27-47.jpg)

*   **Robot Position:** A particle (fake robot) is spawned at a new location with a new field of view.
*   **Synthetic Prediction (Y):** From this particle's position, the map indicates the robot *should* see **two mailboxes and two trees**.
*   **Actual Observation (Z):** The actual robot still observes **one mailbox and two trees**.

![Screenshot at 00:28:15](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-28-15.jpg)

*   To map `Y` (two mailboxes, two trees) to `Z` (one mailbox, two trees), one of the mailboxes in `Y` must have been *missed* (not detected) by the robot.

### Modeling Missed Detections

The probability of seeing nothing from a synthetic view, `P(∅ | Y(x), x)`, needs to be incorporated.

*   **Key Assumption 2: Probabilistic Observation:**
    *   An object `y_i` is observed with some probability, `P(y_i | x)`.
    *   It is *not* observed (missed) with probability `1 - P(y_i | x)`.
    *   This means each object has a binary outcome: either seen or not seen.

*   **Key Assumption 3: Independent Detections:**
    *   For a given position `x` and map, any two object detections are **independent**.
    *   This significantly simplifies the math by avoiding complex covariance calculations. If detections were interdependent (e.g., a broken camera means all objects are missed), the probability statement would become much larger and more complex.
    *   **Caveat:** In reality, independence is often not true (e.g., a broken camera or an occluded view would affect all detections). However, for computational tractability in this model, independence is assumed.

By incorporating these assumptions, the observation model can account for the possibility of missing objects that are actually present in the environment.

---

### Probability of Missing All Objects

[SCREENSHOT-00-29-09]

Given the assumption of independent detections, the probability of missing *all* objects in a synthetic view `Y(x)` is the product of the probabilities of missing each individual object:

`P(∅ | Y(x), x) = Π_{i=0}^{|Y(x)|} (1 - P(y_i | x))`

*   This formula states that if there are `|Y(x)|` objects expected in the view, and each `y_i` has a probability `P(y_i | x)` of being seen, then the probability of seeing *none* of them is the product of `(1 - P(y_i | x))` for all `i`.

## Relaxing Assumptions: "Did We See Nothing as Something?"

The next assumption to be relaxed is that "we never see something that doesn't exist." This introduces the concept of **false detections** or **noise**.

### Example: False Detection

![Screenshot at 00:29:49](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-29-49.jpg)

*   Imagine a robot far off in the distance. Its field of view might only encompass two trees.
*   If the robot *actually observes* two trees and a mailbox, but only two trees are synthetically predicted, then the mailbox must have been "made up" from noise.

### Modeling Noise/False Detections

![Screenshot at 00:30:01](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-30-01.jpg)

*   **Key Assumption 4: Poisson Noise:** Noise is assumed to be **Poisson distributed** in time (meaning the rate of false detections is constant) and **spatially coordinated according to a factor `K(z)`**.
    *   A Poisson variable implies there's always some probability of seeing an object even when nothing is truly there.
    *   While other distributions could be chosen (e.g., based on sensor testing), Poisson is used here for simplicity and consistency with existing research.

*   **Probability of Seeing a Scene from Nothing:** `P(Z | ∅, x)`
    *   This represents the probability of observing a set of objects `Z` when the synthetic view `Y(x)` is empty (i.e., nothing is expected to be there).
    *   It is calculated as the product of individual Poisson variables for each object in `Z`, multiplied by the `K(z)` factor. This implies each false detection is independent.

### What is `K(z)`?

![Screenshot at 00:30:59](notes_screenshots/refined_Advanced_2._Semantic_Localization-(720p30)_screenshots/frame_00-30-59.jpg)

`K(z)` is a factor that accounts for the spatial characteristics of noise-generated objects. It is defined as a product of uniform distributions:

`K(z) = (1 / |C|) * (1 / |S|) * (1 / |B|)`

Where:
*   `|C|`: The number of **possible classifications** (e.g., tree, mailbox).
*   `|S|`: The number of **possible scores** (if the classifier outputs confidence scores).
*   `|B|`: The number of **possible bearings** (if orientation affects observation).

*   **Interpretation:** When an object is "spawned from noise," `K(z)` assumes that *any* type of object (any classification, score, or bearing) is equally probable.
*   **Customization:** If there's prior knowledge about the noise (e.g., noise always gets classified as "tree"), then `K(z)` could be a more intelligent, non-uniform distribution. However, for simplicity, a uniform distribution is used.

## Putting It All Together: Combined Probabilities

Now that all simplifying assumptions have been relaxed, the overall probability `P(Z | Y(x), x)` becomes much more complex, as it must account for:

*   **Misclassification:** An expected object `y` is seen as `z`.
*   **Missed Detections:** An expected object `y` is not seen at all.
*   **False Detections (Noise):** An observed object `z` appears out of nothing (not present in `Y(x)`).
*   **Combinations:** Any combination of these events can occur. For instance:
    *   A scene might lack objects (missed detections) and also have objects added in from noise (false positives).
    *   A scene might have misclassified objects, missed objects, and false positive objects all at once.

Each of these scenarios contributes multiple probability terms that must be multiplied together. As the number of objects and potential error modes increases, the total probability calculation becomes very complex, involving sums over many permutations and combinations of these error types. This highlights the inherent difficulty in building robust semantic localization systems.

---

