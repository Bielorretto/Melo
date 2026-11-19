/* Aide aux tests ft_printf de Melo : chaque appel PF(...) compare ft_printf à printf
 * (même sortie, même valeur de retour), comme le printfTester de Tripouille.
 *
 *   PF("\" %d \", 42", " %d ", 42);
 *      1er argument : l'appel tel qu'il est affiché en cas d'échec
 *      la suite     : le format et les arguments, donnés à snprintf et à ft_printf
 *   PF_DONE();   à la fin : le test échoue s'il y a eu au moins un cas KO
 *
 * La sortie de ft_printf est capturée dans un fichier temporaire (fd 1 redirigé).
 * Avant chaque appel, « melo-appel: ft_printf(...) » est écrit sur stderr : en cas de
 * crash ou de timeout, Melo affiche l'appel qui était en cours. */
#ifndef MELO_PRINTF_H
# define MELO_PRINTF_H

# include <limits.h>
# include <stdint.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# include "ft_printf.h"

# define MELO_PF_BUF 8192

static char	g_melo_exp[MELO_PF_BUF];
static char	g_melo_got[MELO_PF_BUF];
static int	g_melo_saved_fd = -1;
static FILE	*g_melo_tmp = NULL;

/* Premier cas en échec : affiché à la fin, avec le nombre total de cas en échec. */
static char	g_melo_first_call[512];
static char	g_melo_first_got[1024];
static char	g_melo_first_exp[1024];
static int	g_melo_fails = 0;

static inline size_t	melo_pf_putc(char *out, size_t pos, size_t size, unsigned char c)
{
	char	tmp[8];
	int		n;

	if (c == '\n')
		n = snprintf(tmp, sizeof(tmp), "\\n");
	else if (c == '\t')
		n = snprintf(tmp, sizeof(tmp), "\\t");
	else if (c == '"' || c == '\\')
		n = snprintf(tmp, sizeof(tmp), "\\%c", c);
	else if (c < 32 || c >= 127)
		n = snprintf(tmp, sizeof(tmp), "\\%03o", c);
	else
		n = snprintf(tmp, sizeof(tmp), "%c", c);
	if (pos + n < size)
	{
		memcpy(out + pos, tmp, n);
		pos += n;
	}
	out[pos] = '\0';
	return (pos);
}

/* out = n octets entre guillemets à partir de start (70 au plus), puis « , renvoie r ». */
static inline void	melo_pf_show(char *out, size_t size, const char *p, size_t n,
	size_t start, int ret)
{
	size_t	i;
	size_t	pos;

	if (start > n)
		start = n;
	pos = snprintf(out, size, "%s\"", start > 0 ? "..." : "");
	for (i = start; i < n && i < start + 70; i++)
		pos = melo_pf_putc(out, pos, size, (unsigned char)p[i]);
	if (i < n)
		snprintf(out + pos, size - pos, "\"... (%zu octets en tout), renvoie %d", n, ret);
	else
		snprintf(out + pos, size - pos, "\", renvoie %d", ret);
}

static inline void	melo_pf_begin(const char *call)
{
	char	line[600];
	int		len;

	len = snprintf(line, sizeof(line), "melo-appel: ft_printf(%s)\n", call);
	if (len > (int)sizeof(line) - 1)
		len = sizeof(line) - 1;
	if (write(2, line, len) < 0)
		return ;
	fflush(stdout);
	g_melo_tmp = tmpfile();
	g_melo_saved_fd = dup(1);
	if (g_melo_tmp)
		dup2(fileno(g_melo_tmp), 1);
}

static inline void	melo_pf_end(const char *call, int exp_ret, int got_ret)
{
	size_t	got_len;
	size_t	exp_len;
	size_t	diff;
	ssize_t	r;

	dup2(g_melo_saved_fd, 1);
	close(g_melo_saved_fd);
	got_len = 0;
	if (g_melo_tmp)
	{
		lseek(fileno(g_melo_tmp), 0, SEEK_SET);
		while (got_len < MELO_PF_BUF
			&& (r = read(fileno(g_melo_tmp), g_melo_got + got_len, MELO_PF_BUF - got_len)) > 0)
			got_len += (size_t)r;
		fclose(g_melo_tmp);
		g_melo_tmp = NULL;
	}
	exp_len = exp_ret < 0 ? 0 : (size_t)exp_ret;
	if (exp_len > MELO_PF_BUF - 1)
		exp_len = MELO_PF_BUF - 1;
	if (got_len == exp_len && memcmp(g_melo_got, g_melo_exp, exp_len) == 0 && got_ret == exp_ret)
		return ;
	if (g_melo_fails++ > 0)
		return ;
	/* Fenêtre autour de la première différence pour les longues sorties. */
	diff = 0;
	while (diff < got_len && diff < exp_len && g_melo_got[diff] == g_melo_exp[diff])
		diff++;
	diff = diff > 30 && (got_len > 70 || exp_len > 70) ? diff - 20 : 0;
	snprintf(g_melo_first_call, sizeof(g_melo_first_call), "%s", call);
	melo_pf_show(g_melo_first_got, sizeof(g_melo_first_got), g_melo_got, got_len, diff, got_ret);
	melo_pf_show(g_melo_first_exp, sizeof(g_melo_first_exp), g_melo_exp, exp_len, diff, exp_ret);
}

/* À la fin du test : affiche le premier cas en échec (et combien d'autres). */
static inline int	melo_pf_done(void)
{
	char	line[600];
	int		len;

	if (g_melo_fails == 0)
		return (0);
	len = snprintf(line, sizeof(line), "melo-appel: ft_printf(%s)\n", g_melo_first_call);
	if (len > (int)sizeof(line) - 1)
		len = sizeof(line) - 1;
	if (write(2, line, len) < 0)
		return (1);
	printf("obtenu : %s", g_melo_first_got);
	if (g_melo_fails > 1)
		printf("   (+ %d autre(s) cas KO dans ce test)", g_melo_fails - 1);
	printf("\nattendu : %s (comme printf)\n", g_melo_first_exp);
	return (1);
}

# define PF(call, ...) \
	do { \
		int melo_exp_ = snprintf(g_melo_exp, MELO_PF_BUF, __VA_ARGS__); \
		melo_pf_begin(call); \
		int melo_got_ = ft_printf(__VA_ARGS__); \
		melo_pf_end(call, melo_exp_, melo_got_); \
	} while (0)

# define PF_DONE() \
	do { \
		if (melo_pf_done()) \
			return (1); \
	} while (0)

#endif
