const LINK_API_BASE_URL = 'http://157.151.249.89:8080'
const LINK_API_KEY = 'VbO+Mv!1bI0q7AVq'

const UNLINKED_PLAYERS = new Map()

function apiHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': LINK_API_KEY
  }
}

function fetchLinkStatus(player, callback) {
  const username = encodeURIComponent(String(player.username))
  const url = `${LINK_API_BASE_URL}/minecraft/${username}/status`

  FetchJS.fetch(
    url,
    'GET',
    apiHeaders(),
    null,
    null,
    10000,
    data => {
      try {
        const json = JSON.parse(String(data))
        callback(json)
      } catch (err) {
        console.error('[Link] Invalid JSON response: ' + err)
        callback({ ok: false, error: 'Invalid JSON from link API' })
      }
    }
  )
}

function queueUnlinked(player) {
  const position = {
    x: player.x,
    y: player.y,
    z: player.z
  }

  UNLINKED_PLAYERS.set(String(player.uuid), {
    ...position,
    warnedAt: 0
  })
}

function clearUnlinked(player) {
  UNLINKED_PLAYERS.delete(String(player.uuid))
}

function applyFtbRanks(player, ranks) {
  if (!Array.isArray(ranks) || ranks.length === 0) {
    return
  }

  ranks.forEach(rank => {
    const rankName = String(rank || '').trim()
    if (!rankName) {
      return
    }

    // best effort auto-create if rank does not exist
    player.server.runCommandSilent(`ftbranks create ${rankName}`)
    player.server.runCommandSilent(`ftbranks add ${player.username} ${rankName}`)
  })
}

function sendNotLinkedReminder(player) {
  player.tell(Component.red('⚠ You are not linked. Run /link and finish /linkmc in Discord.'))
}

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

        const jsonBody = JSON.stringify({
          minecraft_name: username,
          minecraft_uuid: uuid
        })

        FetchJS.fetch(
          url,
          'POST',
          apiHeaders(),
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
            player.tell(Component.yellow('Your code: ').append(Component.aqua(code)))
            player.tell(Component.green('Run in Discord: ').append(Component.white('/linkmc ' + code)))

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

  event.register(
    Commands.literal('linked')
      .executes(ctx => {
        const player = ctx.source.player
        if (!player) {
          ctx.source.sendFailure(Component.red('Only players can use this command.'))
          return 0
        }

        fetchLinkStatus(player, json => {
          if (!json.ok) {
            player.tell(Component.red('❌ Link check failed. Try again shortly.'))
            return
          }

          if (json.linked) {
            player.tell(Component.green('✔ Linked to Discord. Access granted.'))
            clearUnlinked(player)
          } else {
            player.tell(Component.red('❌ Not linked. Run /link to connect your Discord.'))
            queueUnlinked(player)
          }
        })

        return 1
      })
  )
})

PlayerEvents.loggedIn(event => {
  const player = event.player

  fetchLinkStatus(player, json => {
    if (json.ok && json.linked) {
      clearUnlinked(player)
      applyFtbRanks(player, json.ftb_ranks || [])
      player.tell(Component.green('✔ Discord link detected. Nation ranks synced.'))
      return
    }

    queueUnlinked(player)
    sendNotLinkedReminder(player)
  })
})

PlayerEvents.loggedOut(event => {
  clearUnlinked(event.player)
})

PlayerEvents.tick(event => {
  const player = event.player
  const key = String(player.uuid)
  const state = UNLINKED_PLAYERS.get(key)

  if (!state) {
    return
  }

  const movedTooFar = Math.abs(player.x - state.x) > 4 || Math.abs(player.z - state.z) > 4
  if (movedTooFar) {
    player.teleportTo(state.x, state.y, state.z)
  }

  const now = Date.now()
  if (now - state.warnedAt > 10000) {
    sendNotLinkedReminder(player)
    state.warnedAt = now
    UNLINKED_PLAYERS.set(key, state)
  }
})

PlayerEvents.chat(event => {
  const key = String(event.player.uuid)
  if (!UNLINKED_PLAYERS.has(key)) {
    return
  }

  event.cancel()
  event.player.tell(Component.red('❌ Chat is disabled until you link your Discord with /link.'))
})

PlayerEvents.rightClickedEntity(event => {
  const key = String(event.player.uuid)
  if (!UNLINKED_PLAYERS.has(key)) {
    return
  }

  const entityType = String(event.target.type || '')
  if (entityType.includes('villager') || entityType.includes('merchant')) {
    event.cancel()
    event.player.tell(Component.red('❌ Trading is disabled until Discord is linked.'))
  }
})
