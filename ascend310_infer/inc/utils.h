

#ifndef MINDSPORE_INFERENCE_UTILS_H_
#define MINDSPORE_INFERENCE_UTILS_H_

#include <sys/stat.h>
#include <dirent.h>
#include <vector>
#include <string>
#include <memory>
#include "include/api/types.h"

DIR *OpenDir(std::string_view dirName);
std::string RealPath(std::string_view path);
mindspore::MSTensor ReadFileToTensor(const std::string &file);
int WriteResult(const std::string&, const std::vector<mindspore::MSTensor>&, const std::string&);
std::vector<std::string> GetAllFiles(std::string_view dir_name);

#endif
