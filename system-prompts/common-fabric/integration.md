### Run browser integration tests without foreground windows

Set `HEADLESS=1` whenever an integration test launches a browser. The labs integration shell passes this setting 
to the shared browser launcher, which starts Chrome for Testing with `--headless=new` and `--hide-scrollbars`.

Before a long browser test run, verify that the top-level Chrome for Testing command contains `--headless=new`. 
Headless mode must run the same test and assertions as headed mode.

Use headed mode only when the behavior under investigation requires a visible window.
