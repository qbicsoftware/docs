# QBiC Documentation
Welcome to QBiC's technical documentation pages. Last update: {% now 'utc', '%d %b %Y' %})

Project reports are generated automatically during builds, while this summary is generated once per day. So come back often to get the latest reports. 

## Table of Contents
{% for repo, reports in cookiecutter.repos|dictsort %}
  - [{{loop.index}}. {{ repo }}](#{{loop.index}}-{{ repo }})
{%- endfor %}

{% for repo, reports in cookiecutter.repos|dictsort %}
### {{ loop.index }}. {{ repo }}
GitHub link: [https://github.com/qbicsoftware/{{ repo }}](https://github.com/qbicsoftware/{{ repo }})


#### SNAPSHOT Reports
    {%- if 'development' in reports %}
[Latest SNAPSHOT report]({{ reports['development'] }})
    {%- else %}
We're sorry, there are no available SNAPSHOT reports for this project.
    {%- endif %}


#### Release Reports
    {%- for report, link in reports|dictsort if report != 'development' %}
  - [{{ report }}]({{ link }})
    {%- else %}
We're sorry, there are no available releases reports for this project.
    {%- endfor %}

{% endfor %}