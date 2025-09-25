#include <unistd.h>
#include <stdio.h>

int main(int argc, char **argv)
{
  if (isatty(fileno(stdin))){
  	int c;
	FILE *file;
	file = fopen("./flag", "r");
	if (file) {
	    while ((c = getc(file)) != EOF)
	        putchar(c);
	    fclose(file);
	}
  }
  else
    puts("Only readable by a TTY shell !");
  return 0;
}

