# Loom walkthrough script (about 7 minutes)

Legend: 🖥 screen, 🖱 what you do, 🎙 what you say.

## Before you record

1. Open `https://truck-routing-api-owru.onrender.com/api/health` once to wake the Render free tier.
2. Open these tabs in this order:
   - **Tab 1:** live app, `https://wisteriatlas.github.io/truckrouting/`
   - **Tab 2:** `https://github.com/wisteriatlas/truckrouting/blob/master/docs/ARCHITECTURE.md`
   - **Tab 3:** repo root, `https://github.com/wisteriatlas/truckrouting`
   - **Tab 4:** VS Code with `backend/routing/risk.py` and `recommend.py` open, and a terminal in `backend`
3. Do one test run in Tab 1, then reload so it starts clean.
4. Close other tabs and notifications. Set browser zoom to about 110-125%.
5. Pick a trip where the weather gives some High or Severe miles if you can. A heavy load helps the load rules show up.

---

## Chapter 1: Overview (0:00-0:30)

🖥 **Tab 1:** the live app, empty.
🖱 Nothing to click. Move the mouse over the form, then the map.

🎙 "Hi, I'm [name]. This is my submission for the Weather-Aware Truck Routing assessment. The app takes an origin, destination, departure time and load weight. It generates three route options, checks the forecast at the time the truck will actually be at each point, scores the weather risk, and recommends the safest route. In the next few minutes I'll show what I built, how it works, and the key decisions behind it."

---

## Chapter 2: Requirements and what I built (0:30-2:30)

🖥 **Tab 2:** the architecture page, top, the Requirements coverage table.
🖱 Scroll slowly down the table.

🎙 "First, the requirements. This table maps each one to where it lives in the code. Now let me show them working."

🖥 **Switch to Tab 1.**
🖱 1) Type the origin and pick it from the dropdown. 2) Do the same for the destination. 3) Set the departure time and load. 4) Click **Find safest route**.

🎙 "The user enters origin, destination, departure time and load. Search-as-you-type gives me real coordinates. The backend gets three routes from the OSRM routing API, adding detours if it returns fewer than three distinct ones. Along each route I place a checkpoint every 10, 25 or 50 miles depending on trip length, and estimate the truck's arrival time at each."

🖥 **Tab 1:** results appear.
🖱 1) Hover over the three route cards. 2) Click a checkpoint dot to open its popup. 3) Click a row in the checkpoint table so the map flies to it.

🎙 "On the map you see all three routes, with checkpoints coloured by risk, and a card for each route with distance, ETA, and miles at each risk level. Each checkpoint shows its ETA, wind, rain, snow and risk level. The recommended route has a badge and a one-line reason."

*If the analysis is slow, keep talking: "it's batching the weather calls now."*

---

## Chapter 3: Architecture (2:30-3:30)

🖥 **Tab 2:** scroll to **System overview**, then **What happens on one request**.
🖱 Trace the first diagram with the cursor from left to right. Then trace the sequence diagram from top to bottom.

🎙 "Here's the architecture. On the left is the React app on GitHub Pages, with MapLibre for the map. It talks to a Django API on Render, which calls three free services: OSRM for routes, Open-Meteo for weather, and geocoders for place search.

Let's follow one request. The browser sends one request. Django gets the routes, builds checkpoints with ETAs, and makes one batched weather call for all checkpoints plus the heatmap grid. It's cached and fetched in parallel. Then it picks the forecast hour nearest each ETA, classifies the risk, ranks the routes, and returns everything in one response.

One design choice: the core logic is pure functions with no network calls, which made it easy to test."

---

## Chapter 4: Core logic (3:30-5:15)

🖥 **Tab 2:** scroll to **Risk classification**.
🖱 Follow the flowchart arrows with the cursor.

🎙 "This is the heart of the assessment. Each checkpoint gets a level: Low, Moderate, High, Severe or No Travel. I band wind, rain and snow separately using the spec's thresholds, and take the worst of the three. Then the load rules apply. Wind of 55 mph or more is No Travel for any load. Wind of 45 to 54 with a load over 30,000 pounds is No Travel. Wind of 35 to 44 with a load over 40,000 pounds is raised to Severe. The load rules can only make the risk worse."

🖥 **Tab 4:** VS Code, `risk.py`, then the terminal.
🖱 1) Scroll to `classify` and point at it. 2) Switch to the terminal. 3) Run `.venv\Scripts\python -m pytest`.

🎙 "The logic is about 50 lines. I have 34 tests covering every band edge, for example 24.9 versus 25 mph, and each load override. They all pass."

🖥 **Tab 2:** scroll to **Route recommendation**. Then **Tab 4:** `recommend.py`.
🖱 Point at the numbered sort key in the diagram, then at the `rank_key` line.

🎙 "For the recommendation, I add up how many miles of each route fall in each risk level. Then I compare routes in the spec's order: fewest Severe miles, then fewest High miles, then lowest average risk, then shortest time. One addition of mine: I compare No Travel miles first. A route you can't drive shouldn't win. It's documented in the README."

---

## Chapter 5: Map and heatmap (5:15-6:15)

🖥 **Tab 1:** the live app, heatmap slider at the bottom of the map.
🖱 1) Drag the slider slowly from 0 to 48. 2) Press **Play** and let it run for about 5 seconds. 3) Untick and re-tick **Weather heatmap**.

🎙 "Now the heatmap. Along the corridor of all three routes I sample up to 240 points. For each point I compute the risk for every hour of the next 48, using the same classify function and the same load. All of this comes down with the first response.

That's why the slider is smooth. Moving it doesn't call the server. It just swaps the hour in one map data source, once per frame. I draw it as blurred circles coloured by risk level, instead of a density heatmap, so overlapping areas don't look worse than they really are."

---

## Chapter 6: Decisions and wrap-up (6:15-7:00)

🖥 **Tab 2:** scroll to **Design decisions**. Then **Tab 3:** the repo root.
🖱 Point at each bullet in the list. Then show the README and file tree.

🎙 "A few decisions worth mentioning. I used OSRM instead of OpenRouteService because ORS only gives alternative routes on short trips. OSRM uses a car profile, so I cap truck speed at 62 mph. Place search falls back across three providers, because one blocks hosted servers. And I used only free APIs, so there are no keys to set up.

If I had more time, I'd add a true truck-routing engine, wind gusts, and a 'leave later' suggestion. The code, README and diagrams are all in the repo. Thanks for watching."

---

## If something goes wrong

- **Running long:** shorten Chapter 6 and keep Chapter 4.
- **App fails live:** go to Tab 2 and carry on; the diagrams still carry the explanation.
- **All routes show Low risk:** say so honestly, and show the tests and the load rules instead.
