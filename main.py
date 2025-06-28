async def update_roles_and_announce(member, total_xp):
    guild = member.guild

    # Trova il livello e ruolo giusto (massimo livello raggiunto)
    eligible_levels = [(xp_req, role_id) for xp_req, role_id in ROLE_LEVELS.items() if total_xp >= xp_req]
    if not eligible_levels:
        return None

    max_xp_req, role_id_to_add = max(eligible_levels, key=lambda x: x[0])
    role_to_add = guild.get_role(role_id_to_add)
    if not role_to_add:
        return None

    # Se ha già il ruolo giusto, non fare nulla
    if role_to_add in member.roles:
        return None

    try:
        await member.add_roles(role_to_add, reason="Aggiornamento ruolo per XP")

        # Manda embed nel canale level-up
        channel = guild.get_channel(CHANNEL_LEVELUP)
        if channel:
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Congratulazioni {member.mention}, hai raggiunto il ruolo **{role_to_add.name}**!",
                color=XP_COLOR
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"XP raggiunti: {total_xp}")
            await channel.send(embed=embed)

        print(f"Ruolo {role_to_add.name} assegnato a {member.display_name}")
        return role_to_add.name
    except Exception as e:
        print(f"Errore assegnazione ruoli a {member.display_name}: {e}")
        return None
