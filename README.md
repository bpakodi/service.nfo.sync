# service.nfo.sync Kodi addon

***warning: still in alpha version, use at your own risk!***


## Overview
Keeps Kodi's video library and .nfo files closely synchronized, by enriching the way Kodi manages these nfo files.

This set of tools is intended for advanced Kodi users, with large libraries and / or multi-room configurations.

It helps maintaining a standard / centralized / sustainable source of video metadata in multiple .nfo files, as well as keeping Kodi instances updated all along.

If you are not confident with scrapers and .nfo file processing in Kodi, this addon is probably not meant for you...

Main functionalities:
 * import: refresh Kodi entries when a nfo is updated
 * export: update the nfo when an entry is modified (watched status)
 * automate behavior by catching the relevant Kodi events
 * apply user-defined scripts to modify NFO content on-the-fly very easily

**Note:** only movies are covered for the moment... please be patient :-)

## Configuration
Set the **Local information only** scraper on all your movie media sources.
Optionally, you may want to set the following settings in Kodi:
 * *Update library on startup*:
   * Settings > Media > Library
 * *importwatchedstate* and *importresumepoint*:
   * see [Kodi wiki / advancedsettings.xml](https://kodi.wiki/view/Advancedsettings.xml#videolibrary) for details


## Compatibility
Kodi 18 (Leia) only  

## Known limitations and roadmap
Still a long way to go... some possible developments:
 * Integrate TV shows and music videos
 * Automatically set some tags depending on user-defined criteria: audio language, file location, ...
 * Make it compatible with Krypton?
 * Export resume point
