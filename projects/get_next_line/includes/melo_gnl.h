/* Aide aux tests get_next_line de Melo (cas repris du gnlTester de Tripouille).
 *
 *   GNL(fd, "ligne\n", "files/nl");   appelle get_next_line(fd) et compare à la ligne
 *   GNL(fd, NULL, "files/nl");        attendue (NULL : fin de fichier ou erreur)
 *
 * Le test s'arrête au premier appel en échec. Avant chaque appel, « melo-appel: ... »
 * est écrit sur stderr : en cas de crash ou de timeout, Melo affiche l'appel en cours.
 * MELO_GNL_HEADER : header inclus (get_next_line.h, ou get_next_line_bonus.h pour le bonus). */
#ifndef MELO_GNL_H
# define MELO_GNL_H

# include <fcntl.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# ifndef MELO_GNL_HEADER
#  define MELO_GNL_HEADER "get_next_line.h"
# endif
# include MELO_GNL_HEADER

static int	g_melo_call = 0;

static inline void	melo_gnl_putc(unsigned char c)
{
	if (c == '\n')
		printf("\\n");
	else if (c == '"' || c == '\\')
		printf("\\%c", c);
	else if (c < 32 || c >= 127)
		printf("\\%03o", c);
	else
		putchar(c);
}

/* Chaîne entre guillemets à partir de start (70 caractères au plus). */
static inline void	melo_gnl_show(const char *s, size_t start)
{
	size_t	n;
	size_t	i;

	if (!s)
	{
		printf("NULL");
		return ;
	}
	n = strlen(s);
	if (start > n)
		start = n;
	if (start)
		printf("...");
	putchar('"');
	for (i = start; i < n && i < start + 70; i++)
		melo_gnl_putc((unsigned char)s[i]);
	putchar('"');
	if (start || i < n)
		printf(" (%zu caractères)", n);
}

static inline int	melo_gnl(int fd, const char *exp, const char *what)
{
	char	marker[256];
	char	*line;
	size_t	diff;
	int		len;
	int		ok;

	g_melo_call++;
	len = snprintf(marker, sizeof(marker),
			"melo-appel: get_next_line(%s) — appel n°%d\n", what, g_melo_call);
	if (len > (int)sizeof(marker) - 1)
		len = sizeof(marker) - 1;
	if (write(2, marker, len) < 0)
		return (1);
	line = get_next_line(fd);
	if (!exp)
		ok = line == NULL;
	else
		ok = line != NULL && strcmp(line, exp) == 0;
	if (ok)
	{
		free(line);
		return (0);
	}
	diff = 0;
	while (line && exp && line[diff] && line[diff] == exp[diff])
		diff++;
	diff = diff > 40 ? diff - 20 : 0;
	printf("obtenu : ");
	melo_gnl_show(line, diff);
	printf("\nattendu : ");
	melo_gnl_show(exp, diff);
	printf("\n");
	free(line);
	return (1);
}

# define GNL(fd, exp, what) \
	do { \
		if (melo_gnl(fd, exp, what)) \
			return (1); \
	} while (0)

/* Chaîne de n chiffres "0123456789012...", suivie de '\n' si nl (pour les grosses lignes). */
static inline char	*melo_digits(size_t n, int nl)
{
	char	*s;
	size_t	i;

	s = malloc(n + 2);
	if (!s)
		exit(2);
	for (i = 0; i < n; i++)
		s[i] = '0' + i % 10;
	if (nl)
		s[i++] = '\n';
	s[i] = '\0';
	return (s);
}

#endif
