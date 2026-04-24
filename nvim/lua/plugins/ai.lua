return {
	{
		"olimorris/codecompanion.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-treesitter/nvim-treesitter",
		},
		opts = {
			strategies = {
				chat = { adapter = "claude_code" },
				inline = { adapter = "claude_code" },
			},
			adapters = {
				acp = {
					claude_code = function()
						return require("codecompanion.adapters").extend("claude_code", {
							env = {
								CLAUDE_CODE_OAUTH_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN",
								CLAUDE_CODE_EXECUTABLE = "/Users/nielsmadan/.local/bin/claude",
							},
						})
					end,
				},
			},
		},
		cmd = {
			"CodeCompanion",
			"CodeCompanionChat",
			"CodeCompanionActions",
			"CodeCompanionCmd",
		},
    -- stylua: ignore
    keys = {
      { "<leader>aa", "<cmd>CodeCompanionActions<cr>",      mode = { "n", "v" }, desc = "AI Actions" },
      { "<leader>at", "<cmd>CodeCompanionChat Toggle<cr>",  mode = { "n", "v" }, desc = "AI Chat Toggle" },
      { "<leader>ac", "<cmd>CodeCompanionChat Add<cr>",     mode = "v",          desc = "AI Chat Add Selection" },
      { "<leader>ai", ":CodeCompanion ",                    mode = { "n", "v" }, desc = "AI Inline" },
    },
	},
}
