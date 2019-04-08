# QBiC Documentation
Welcome to QBiC's technical documentation pages. 

Project reports are generated automatically during builds, while this summary is generated daily. So come back often to get the latest reports. 

## List of projects (by repository name)
{% for repo_name, repo in cookiecutter.repos|dictsort %}
  - [{{loop.index}}. {{ repo_name }}](#{{loop.index}}-{{ repo_name }})
{%- endfor %}

{% for repo_name, repo in cookiecutter.repos|dictsort %}
### {{ loop.index }}. {{ repo_name }}
{{ repo['description'] if repo['description'] else 'No description available for {}.'.format(repo_name) }}

GitHub link: [https://github.com/qbicsoftware/{{ repo_name }}](https://github.com/qbicsoftware/{{ repo_name }})


#### SNAPSHOT reports
    {%- if 'development' in repo['reports'] %}
[Latest SNAPSHOT report]({{ repo['reports']['development'] }})
    {%- else %}
We're sorry, there are no available SNAPSHOT reports for this project. Come back soon!
    {%- endif %}


#### Release reports
    {%- for report_name, report_link in repo['reports']|dictsort if report_name != 'development' %}
  - [{{ report_name }}]({{ report_link }})
    {%- else %}
We're sorry, there are no available release reports for this project. Come back soon!
    {%- endfor %}

{% endfor %}



<sub>Last update: {% now 'utc', '%-d %B %Y, %-H:%M hrs' %}.</sub>
