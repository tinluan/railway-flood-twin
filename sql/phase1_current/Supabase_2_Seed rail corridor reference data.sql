insert into rail.corridor (
    corridor_code,
    corridor_name,
    description
)
values (
    'PK520_PK535',
    'Rail corridor PK520 to PK535',
    'Initial corridor for the railway flood-risk digital twin MVP'
)
on conflict (corridor_code) do nothing;