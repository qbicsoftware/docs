# QBiC Documentation
Documentation (mostly technical) about all the things that have been done at QBiC.

This project generates a [summary](https://qbicsoftware.github.io/docs/) for all QBiC repositories and updates the `gh-pages` branch.

## How to get your reports published
If you generated your report using our [cookecutter-templates-cli tool](https://github.com/qbicsoftware/cookiecutter-templates-cli), then you're good to go. But if you have a non-Java project and still want your reports automatically picked up by the summary, read along.

We are using [GitHub pages](https://pages.github.com/) to host our reports. Everything report-related must be pushed to the `gh-pages` branch of your repository. If you're so inclined, you can check out [.generate-reports.py](https://github.com/qbicsoftware/cookiecutter-templates-cli/blob/development/common-files/%7B%7B%20cookiecutter.artifact_id%20%7D%7D/.generate-reports.py), the script that automatically generates reports. 

When the summary is being generated, a semi-strict structure is required for a report to be included. The root folder of your `gh-pages` branch should look as follows:

```
 reports                   
   ├── development         
   │   └── index.html
   │  
   ├── 1.0.0               
   │   └── index.html
   │  
   ├── 1.0.1               
   │   └── index.html
   │  
   └── 2.0.0               
       └── index.html
```

As you can see, only one "development" version of the reports is assumed. This is presented as a _SNAPSHOT_ report. All other folders are displayed as _Release reports_. Each folder must contain, at the very least, an `index.html` file. The rest is up to you.

The summary is generated once per day in [Travis-CI](http://travis-ci.com) by a nightly build. If you can't wait that long, you can trigger a new build using [Travis-CI's](http://travis-ci.com) UI.
