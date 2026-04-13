const LINK_API_BASE_URL = 'http://157.151.249.89:8080'
const LINK_API_KEY = 'VbO+Mv!1bI0q7AVq'


ServerEvents.commandRegistry(event => {
  const Commands = event.commands

  event.register(
    Commands.literal('link')
      .executes(ctx => {
        const player = ctx.source.player
        if (!player) {
          ctx.source.sendFailure(Component.red('Only players can use this command.'))
          return 0
        }

        const uuid = String(player.uuid)
        const username = String(player.username)
        const url = `${LINK_API_BASE_URL}/link-codes`

        const headers = {
          'Content-Type': 'application/json',
          'X-API-Key': LINK_API_KEY
        }

        const jsonBody = JSON.stringify({
          minecraft_name: username,
          minecraft_uuid: uuid
        })

        FetchJS.fetch(
          url,
          'POST',
          headers,
          jsonBody,
          null,
          10000,
          data => {
            let json

            try {
              json = JSON.parse(String(data))
            } catch (err) {
              console.error('[Link] Invalid JSON response: ' + err)
              player.tell(Component.red('❌ Invalid response from link server.'))
              return
            }

            if (!json.ok) {
              player.tell(Component.red('❌ ' + String(json.error || 'Link failed')))
              return
            }

            const code = String(json.code || '')
            const expiresAt = Number(json.expires_at || 0)

            if (!code) {
              player.tell(Component.red('❌ No code returned from server.'))
              return
            }

            player.tell(Component.gold('=== Discord Account Linking ==='))
            player.tell(
              Component.yellow('Your code: ')
                .append(Component.aqua(code))
            )
            player.tell(
              Component.green('Run in Discord: ')
                .append(Component.white('/linkmc ' + code))
            )

            if (expiresAt > 0) {
              const secondsLeft = Math.max(0, expiresAt - Math.floor(Date.now() / 1000))
              const minutesLeft = Math.max(1, Math.ceil(secondsLeft / 60))
              player.tell(Component.gray('Expires in ~' + minutesLeft + ' minute(s).'))
            }
          }
        )

        return 1
      })
  )
})
