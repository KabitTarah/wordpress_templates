# wordpress_templates
Filling in template posts to generate new posts in WordPress

wp_oauth.json requires:
* client_id = provided by developer.wordpress.com/apps
* client_secret = provided by developer.wordpress.com/apps
* username = WP Username
* password = WP Password
* grant_type = "password"

I'm still not sure how to generate valid OAuth connection from CLI for a WP App

wp_site.json requires:
* site = site URL or site ID#
* template = template post ID

This code is all specific to my use case at https://de.kabit.club

