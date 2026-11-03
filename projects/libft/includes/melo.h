/* Aide aux tests libft de Melo : affichage "obtenu : ... / attendu : ..." sur une ligne
 * (lu par core/runner.py) et capture de ce qui est écrit sur un fd. */
#ifndef MELO_H
# define MELO_H

# include <ctype.h>
# include <fcntl.h>
# include <limits.h>
# include <stdint.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# include "libft.h"

static inline void	melo_putc(unsigned char c)
{
	if (c == '\n')
		printf("\\n");
	else if (c == '\t')
		printf("\\t");
	else if (c == '"')
		printf("\\\"");
	else if (c == '\\')
		printf("\\\\");
	else if (c < 32 || c >= 127)
		printf("\\%03o", c);
	else
		putchar(c);
}

/* Chaîne entre guillemets, échappée, tronquée à 60 caractères. */
static inline void	melo_s(const char *s)
{
	size_t	i;

	if (!s)
	{
		printf("NULL");
		return ;
	}
	putchar('"');
	for (i = 0; s[i] && i < 60; i++)
		melo_putc((unsigned char)s[i]);
	putchar('"');
	if (s[i])
		printf("... (%zu caractères)", strlen(s));
}

/* n octets entre guillemets, \0 compris. */
static inline void	melo_m(const void *p, size_t n)
{
	size_t	i;

	if (!p)
	{
		printf("NULL");
		return ;
	}
	putchar('"');
	for (i = 0; i < n && i < 60; i++)
		melo_putc(((const unsigned char *)p)[i]);
	putchar('"');
	if (i < n)
		printf("... (%zu octets)", n);
}

static inline int	melo_ko_s(const char *got, const char *exp)
{
	printf("obtenu : ");
	melo_s(got);
	printf("\nattendu : ");
	melo_s(exp);
	printf("\n");
	return (1);
}

static inline int	melo_ko_m(const void *got, const void *exp, size_t n)
{
	printf("obtenu : ");
	melo_m(got, n);
	printf("\nattendu : ");
	melo_m(exp, n);
	printf("\n");
	return (1);
}

static inline int	melo_ko_i(long long got, long long exp)
{
	printf("obtenu : %lld\nattendu : %lld\n", got, exp);
	return (1);
}

static inline int	melo_ko_txt(const char *got, const char *exp)
{
	printf("obtenu : %s\nattendu : %s\n", got, exp);
	return (1);
}

/* Décrit un pointeur résultat par rapport au début de la chaîne/zone : "s + 3", "NULL"... */
static inline void	melo_ptr(const void *base, size_t size, const void *p)
{
	if (!p)
		printf("NULL");
	else if ((const char *)p >= (const char *)base
		&& (const char *)p <= (const char *)base + size)
		printf("s + %zu", (size_t)((const char *)p - (const char *)base));
	else
		printf("pointeur en dehors de s (%p)", p);
}

static inline int	melo_ko_ptr(const void *base, size_t size, const void *got, const void *exp)
{
	printf("obtenu : ");
	melo_ptr(base, size, got);
	printf("\nattendu : ");
	melo_ptr(base, size, exp);
	printf("\n");
	return (1);
}

static inline int	melo_sign(long long x)
{
	return ((x > 0) - (x < 0));
}

static inline const char	*melo_sign_txt(long long x)
{
	if (x > 0)
		return ("positif");
	if (x < 0)
		return ("négatif");
	return ("0");
}

/* Capture d'un fd : melo_cap_begin(fds) puis écrire sur fds[1], puis melo_cap_end. */
static inline int	melo_cap_begin(int fds[2])
{
	return (pipe(fds));
}

static inline size_t	melo_cap_end(int fds[2], char *buf, size_t size)
{
	size_t	total;
	ssize_t	r;

	close(fds[1]);
	total = 0;
	while (total + 1 < size && (r = read(fds[0], buf + total, size - 1 - total)) > 0)
		total += (size_t)r;
	buf[total] = '\0';
	close(fds[0]);
	return (total);
}

#endif
