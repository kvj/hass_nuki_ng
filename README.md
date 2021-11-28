## Better support for Nuki devices in the Home Assistant

### Features:
* Supported modes:
  * Nuki Bridge-only, with automatic webhook registration
  * Cloud Web API, without Nuki bridge (Nuki Lock 3.0 Pro). Polling only
  * Hybrid, using best parts of both
* Exposes the detailed device information via sensors
* If supported, enables access control to Nuki authorization objects (keypad codes, accounts)

### Installation:
* Add this repo to the HACS as an Integration
* Add new custom integration (Nuki Lock)
* Input bridge API token and URL and/or web API token

### Screenshots:
<img width="1020" alt="Screenshot 2021-10-11 at 14 02 42" src="https://user-images.githubusercontent.com/159124/136786951-d1ffdb22-637a-49c2-a1ff-43c465a03f0b.png">
