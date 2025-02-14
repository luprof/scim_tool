## SCIM Tool for Netskope

**This is not an official Netskope tool, Netskope support case should be open to perform SCIM operation on a production tenant**

The tool will enumerate useras and groups using the SCIM API on a Netskope tenant, using an API v2 token authorized to access the required endpoints.
With the cmdline options `--action delete` it will delete entries.

```
usage: scim_users_groups.py [-h] --url URL --token TOKEN [--format {pretty,json}] [--type {Users,Groups}]
                            [--action {list,delete,create}] [--id ID] [--delay DELAY] [--username USERNAME] [--email EMAIL]
                            [--first-name FIRST_NAME] [--last-name LAST_NAME] [--display-name DISPLAY_NAME] [--external-id EXTERNAL_ID]
                            [--members MEMBERS] [--add-to-group] [--user-id USER_ID] [--group-id GROUP_ID]
```
                            
