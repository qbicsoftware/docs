# QBiC Documentation
Welcome to QBiC's technical documentation pages. 

Project reports are generated automatically during builds, while this summary is generated daily. So come back often to get the latest reports. 

## List of Projects
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
We're sorry, there are no available SNAPSHOT reports for this project. Come back soon!
    {%- endif %}


#### Release Reports
    {%- for report, link in reports|dictsort if report != 'development' %}
  - [{{ report }}]({{ link }})
    {%- else %}
We're sorry, there are no available releases reports for this project. Come back soon!
    {%- endfor %}

{% endfor %}



<sub>Last update: {% now 'utc', '%-d %B %Y, %-H:%M hrs' %}.</sub>
