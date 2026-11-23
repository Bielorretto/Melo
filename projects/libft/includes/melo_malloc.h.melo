/* Simulation d'échec de malloc. Le test doit être lié avec -Wl,--wrap=malloc :
 * tous les appels à malloc (lib de l'élève comprise) passent par __wrap_malloc.
 *
 *   melo_fail_at(n);   le n-ième malloc (à partir de 0) renverra NULL
 *   ... appel ...
 *   melo_stop();       renvoie 1 si un malloc a bien échoué pendant l'appel
 *
 * Pour allouer dans le test sans être compté : __real_malloc.
 *
 *   melo_alloc_size(p)   taille demandée à malloc pour p (-1 si inconnue)
 *   melo_mcheck(p, n)    1 si p a été alloué avec exactement n octets (sinon affiche
 *                        obtenu / attendu, comme le « MKO » du libftTester de Tripouille) */
#ifndef MELO_MALLOC_H
# define MELO_MALLOC_H

# include <stddef.h>

void		*__real_malloc(size_t size);

static int	g_melo_fail_at = -1;
static int	g_melo_count = 0;
static int	g_melo_failed = 0;

/* Les 4096 dernières allocations : (pointeur, taille demandée). */
# define MELO_ALLOC_LOG 4096

static void		*g_melo_alloc_ptr[MELO_ALLOC_LOG];
static size_t	g_melo_alloc_size[MELO_ALLOC_LOG];
static size_t	g_melo_alloc_n = 0;

void	*__wrap_malloc(size_t size)
{
	void	*p;

	if (g_melo_fail_at >= 0 && g_melo_count++ == g_melo_fail_at)
	{
		g_melo_failed = 1;
		return (NULL);
	}
	p = __real_malloc(size);
	g_melo_alloc_ptr[g_melo_alloc_n % MELO_ALLOC_LOG] = p;
	g_melo_alloc_size[g_melo_alloc_n % MELO_ALLOC_LOG] = size;
	g_melo_alloc_n++;
	return (p);
}

/* Allocation la plus récente qui a renvoyé p (un pointeur libéré peut être réutilisé). */
static inline long long	melo_alloc_size(const void *p)
{
	size_t	i;
	size_t	k;

	if (!p)
		return (-1);
	for (i = 0; i < MELO_ALLOC_LOG && i < g_melo_alloc_n; i++)
	{
		k = (g_melo_alloc_n - 1 - i) % MELO_ALLOC_LOG;
		if (g_melo_alloc_ptr[k] == p)
			return ((long long)g_melo_alloc_size[k]);
	}
	return (-1);
}

static inline int	melo_mcheck(const void *p, size_t expected, const char *what)
{
	long long	got;

	got = melo_alloc_size(p);
	if (got == (long long)expected)
		return (1);
	if (got < 0)
		printf("obtenu : %s n'a pas été alloué avec malloc\n", what);
	else
		printf("obtenu : malloc(%lld) pour %s\n", got, what);
	printf("attendu : malloc(%zu) : la taille exacte (%s)\n", expected,
		got > (long long)expected ? "pas d'octets en trop" : "assez de place");
	return (0);
}

static inline void	melo_fail_at(int n)
{
	g_melo_fail_at = n;
	g_melo_count = 0;
	g_melo_failed = 0;
}

static inline int	melo_stop(void)
{
	g_melo_fail_at = -1;
	return (g_melo_failed);
}

#endif
