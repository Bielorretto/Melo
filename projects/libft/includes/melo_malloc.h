/* Simulation d'échec de malloc. Le test doit être lié avec -Wl,--wrap=malloc :
 * tous les appels à malloc (lib de l'élève comprise) passent par __wrap_malloc.
 *
 *   melo_fail_at(n);   le n-ième malloc (à partir de 0) renverra NULL
 *   ... appel ...
 *   melo_stop();       renvoie 1 si un malloc a bien échoué pendant l'appel
 *
 * Pour allouer dans le test sans être compté : __real_malloc. */
#ifndef MELO_MALLOC_H
# define MELO_MALLOC_H

# include <stddef.h>

void		*__real_malloc(size_t size);

static int	g_melo_fail_at = -1;
static int	g_melo_count = 0;
static int	g_melo_failed = 0;

void	*__wrap_malloc(size_t size)
{
	if (g_melo_fail_at >= 0 && g_melo_count++ == g_melo_fail_at)
	{
		g_melo_failed = 1;
		return (NULL);
	}
	return (__real_malloc(size));
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
