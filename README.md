# service.nfo.sync Kodi addon


**[Please check the project wiki for more information and advanced configuration](https://github.com/bpakodi/service.nfo.sync/wiki)**

**Current version: v0.0.2 (2018-06-19):**
  >**warning: still in alpha version, use at your own risk!**
  >
  >What's new:
  > * User-defined python scripts
  > * Far better logging and error catching
  > * Complete reorganization of classes

## Overview
Extend the way Kodi manages NFO files, with an automatic synchronization of your video library and NFOs altogether.

Also summon some magic and apply tags dynamically to your video entries, thanks to user-defined scripts!

## Main functionalities
 * service: automated processes running in background, triggered by Kodi events
 * import: refresh Kodi entries automatically, when a NFO is updated
 * export: update the NFO automatically, when an entry is modified (watched status only for the moment)
 * custom scripts: fully customize the content of your NFOs, using a simple Python syntax

**Note:** only movies are covered for the moment... please be patient

## Disclaimer:
 * This set of tools is intended for advanced Kodi users, with large libraries and / or multi-room configurations. If you are not confident with scrapers and .nfo file processing in Kodi, this addon is probably not meant for you...
 * It's still alpha version, you know, so use at your own risk!

## Configuration
 1. Set the **Local information only** scraper on all your movie media sources
 2. Check nfo sync configuration
 3. Launch a first library scan and start playing

Optionally, you may also configure the following settings in Kodi:
 * *Update library on startup*:
   * Settings > Media > Library
 * *importwatchedstate* and *importresumepoint*:
   * see [Kodi wiki / advancedsettings.xml](https://kodi.wiki/view/Advancedsettings.xml#videolibrary) for details

## Compatibility
Kodi 18 (Leia) only  

## Known limitations and roadmap
Still a long way to go... some possible developments:
 * Integrate TV shows and music videos
 * Make it compatible with Krypton?
 * Export resume point
